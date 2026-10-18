#!/usr/bin/env python3
"""Analiza un registro DCI LTE FALCON con la biblioteca estándar de Python.

Cada registro de entrada contiene 20 campos separados por espacios. Los archivos
de salida incluyen solo agregados; nunca copian los valores hexadecimales ni RNTI individuales.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

FIELDS = ("timestamp", "sfn", "subframe", "rnti", "direction", "mcs_idx",
          "nof_prb", "tbs_sum", "tbs_0", "tbs_1", "format", "ndi",
          "ndi_1", "harq_idx", "ncce", "L", "cfi", "histval", "nof_bits", "hex")
RESERVED_RNTI_MIN = 65524


@dataclass(frozen=True)
class Record:
    timestamp: float
    sfn: int
    subframe: int
    rnti: int
    direction: int
    nof_prb: int
    mcs_idx: int


def parse_records(path: Path) -> tuple[list[Record], dict[str, int]]:
    counts = {"total_lines": 0, "comment_lines": 0, "blank_lines": 0,
              "valid_rows": 0, "invalid_rows": 0, "schema_errors": 0}
    records = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, raw in enumerate(f, 1):
            counts["total_lines"] += 1
            line = raw.strip()
            if not line:
                counts["blank_lines"] += 1
                continue
            if line.startswith(("#", "%", "//")):
                counts["comment_lines"] += 1
                continue
            cols = line.split()
            if len(cols) != 20:
                counts["invalid_rows"] += 1
                counts["schema_errors"] += 1
                continue
            try:
                t = float(cols[0]); sfn = int(cols[1]); sf = int(cols[2])
                rnti = int(cols[3], 0) if cols[3].lower().startswith("0x") else int(cols[3])
                direction = int(cols[4]); mcs = int(cols[5]); prb = int(cols[6]); tbs = int(cols[7])
                # EyeCore incrementa SFN como contador; puede superar el rango LTE de 10 bits.
                if not math.isfinite(t) or sfn < 0 or not 0 <= sf <= 9:
                    raise ValueError
                if not 0 <= rnti <= 65535 or direction not in (0, 1):
                    raise ValueError
                if not 0 <= mcs <= 31 or not 1 <= prb <= 110 or tbs < 0:
                    raise ValueError
                records.append(Record(t, sfn, sf, rnti, direction, prb, mcs))
                counts["valid_rows"] += 1
            except (ValueError, OverflowError):
                counts["invalid_rows"] += 1
    return records, counts


def _slug(label: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip()).strip(".-_")
    if not slug or slug in (".", ".."):
        raise ValueError("la etiqueta de sesión debe incluir letras o números")
    return slug[:80]


def _safe_under(root: Path, *parts: str) -> Path:
    base = root.resolve()
    dest = base.joinpath(*parts).resolve()
    if dest != base and base not in dest.parents:
        raise ValueError("la ruta de salida queda fuera de la carpeta de salida")
    return dest


def _aggregate(records: list[Record], window: float, origin: float):
    bins = defaultdict(lambda: {"ul_prb_assignments": 0, "dl_prb_assignments": 0,
                                "dci_records": 0, "observed_nonreserved_rnti_count": 0,
                                "_rntis": set()})
    for r in records:
        idx = int(math.floor((r.timestamp - origin) / window + 1e-12))
        b = bins[idx]
        b["dci_records"] += 1
        key = "ul_prb_assignments" if r.direction == 0 else "dl_prb_assignments"
        b[key] += r.nof_prb
        if r.rnti != 0 and r.rnti < RESERVED_RNTI_MIN:
            b["_rntis"].add(r.rnti)
    for b in bins.values():
        b["observed_nonreserved_rnti_count"] = len(b.pop("_rntis"))
    return bins


def _mcs_counts(records: list[Record]):
    counts = {direction: [0] * 32 for direction in (0, 1)}
    for r in records:
        counts[r.direction][r.mcs_idx] += 1
    return counts


def _write_svg(path: Path, bins: dict, window: float, frequency: float):
    width, height, left, right, top = 1040, 690, 90, 35, 55
    plot_w = width-left-right
    panels = [("Tasa observada de asignaciones PRB", "Asignaciones PRB por segundo", "#1769aa"),
              ("Registros DCI decodificados", "Registros por intervalo", "#c65d17"),
              ("RNTI no reservados observados", "Identificadores distintos por intervalo", "#238636")]
    n = max(1, max(bins, default=0) + 1)
    end = n * window
    maxes = [max([((v["ul_prb_assignments"]+v["dl_prb_assignments"])/window)
                   for v in bins.values()] or [1]),
             max([v["dci_records"] for v in bins.values()] or [1]),
             max([v["observed_nonreserved_rnti_count"] for v in bins.values()] or [1])]
    maxes = [max(1, x) for x in maxes]
    elems = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#fff"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#182230}.grid{stroke:#d9e0e8;stroke-width:1}.axis{stroke:#425466;stroke-width:1.2}</style>',
             f'<text x="{left}" y="27" font-size="19" font-weight="bold">Actividad DCI de LTE FALCON · {frequency:g} MHz</text>']
    panel_h = 166
    for pi, (title, ylabel, color) in enumerate(panels):
        y0 = top + pi*190
        plot_top, plot_bottom = y0+22, y0+panel_h-30
        elems.append(f'<text x="{left}" y="{y0+14}" font-size="14" font-weight="bold">{title}</text>')
        for j in range(4):
            y = plot_bottom-(plot_bottom-plot_top)*j/3
            elems.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}"/>')
            elems.append(f'<text x="{left-9}" y="{y+4:.1f}" text-anchor="end" font-size="10">{maxes[pi]*j/3:.1f}</text>')
        elems.append(f'<line class="axis" x1="{left}" y1="{plot_top}" x2="{left}" y2="{plot_bottom}"/><line class="axis" x1="{left}" y1="{plot_bottom}" x2="{left+plot_w}" y2="{plot_bottom}"/>')
        elems.append(f'<text transform="translate(19 {((plot_top+plot_bottom)/2):.1f}) rotate(-90)" text-anchor="middle" font-size="11">{ylabel}</text>')
        # Separa las líneas en intervalos ausentes para no dibujar la ausencia como cero.
        segments=[]; current=[]
        for i in range(n):
            b=bins.get(i)
            if b is None:
                if current: segments.append(current); current=[]
                continue
            val = ((b["ul_prb_assignments"]+b["dl_prb_assignments"])/window if pi == 0 else
                   b["dci_records"] if pi == 1 else b["observed_nonreserved_rnti_count"])
            x=left+plot_w*(i+0.5)/n
            y=plot_bottom-(plot_bottom-plot_top)*val/maxes[pi]
            current.append((x,y))
        if current: segments.append(current)
        for seg in segments:
            if len(seg)==1:
                x,y=seg[0]; elems.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"/>')
            else:
                points=" ".join(f"{x:.2f},{y:.2f}" for x,y in seg)
                elems.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.2"/>')
        for xt in range(5):
            value=end*xt/4; x=left+plot_w*xt/4
            elems.append(f'<line class="axis" x1="{x:.1f}" y1="{plot_bottom}" x2="{x:.1f}" y2="{plot_bottom+4}"/><text x="{x:.1f}" y="{plot_bottom+17}" text-anchor="middle" font-size="10">{value:.1f}</text>')
    elems.append(f'<text x="{left+plot_w/2}" y="669" text-anchor="middle" font-size="11">Segundos desde la primera marca de tiempo válida</text>')
    elems.append('<text x="90" y="686" font-size="9" fill="#596579">Solo registros decodificados observados · se omiten los intervalos sin datos</text>')
    elems.append('</svg>')
    path.write_text("\n".join(elems), encoding="utf-8")


def _write_mcs_svg(path: Path, counts: dict):
    width, height = 920, 430
    left, right, top, bottom = 76, 24, 55, 330
    max_count = max(1, max(counts[0] + counts[1]))
    points = []
    for direction, color in ((0, "#1769aa"), (1, "#c65d17")):
        pts = []
        for mcs, count in enumerate(counts[direction]):
            x = left + (width-left-right) * mcs / 31
            y = bottom - (bottom-top) * count / max_count
            pts.append((x, y))
        points.append((direction, color, pts))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/><style>text{font-family:Arial,sans-serif;fill:#182230}</style>',
             '<text x="76" y="28" font-size="18" font-weight="bold">Distribución MCS de registros decodificados observados</text>',
             f'<line x1="{left}" y1="{bottom}" x2="{width-right}" y2="{bottom}" stroke="#425466"/>',
             f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#425466"/>']
    for i in range(4):
        y = bottom - (bottom-top)*i/3
        val = max_count*i/3
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#d9e0e8"/><text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="10">{val:.1f}</text>')
    for mcs in range(0, 32, 2):
        x = left + (width-left-right)*mcs/31
        parts.append(f'<text x="{x:.1f}" y="{bottom+18}" text-anchor="middle" font-size="10">{mcs}</text>')
    for direction, color, pts in points:
        poly = " ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
        parts.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/>')
        label = "UL" if direction == 0 else "DL"
        parts.append(f'<line x1="{720+direction*80}" y1="48" x2="{744+direction*80}" y2="48" stroke="{color}" stroke-width="3"/><text x="{750+direction*80}" y="52" font-size="11">{label}</text>')
    parts.append('<text x="460" y="382" text-anchor="middle" font-size="11">Índice MCS</text><text transform="translate(18 195) rotate(-90)" text-anchor="middle" font-size="11">Registros DCI decodificados</text>')
    parts.append('<text x="76" y="405" font-size="9">UL: subida · DL: bajada. Los conteos MCS describen etiquetas decodificadas; no miden directamente la calidad del canal.</text></svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def analyze(input_path: Path, label: str, frequency: float, window: float,
            output_root: Path, console_text: str | None = None) -> dict:
    slug = _slug(label)
    if not math.isfinite(frequency) or frequency <= 0 or not math.isfinite(window) or window <= 0:
        raise ValueError("la frecuencia y el intervalo deben ser números positivos y finitos")
    records, counts = parse_records(input_path)
    if not records:
        raise ValueError(f"no se encontraron registros válidos ({counts['invalid_rows']} filas no válidas)")
    origin=min(r.timestamp for r in records); last=max(r.timestamp for r in records)
    duration=last-origin
    if not math.isfinite(duration):
        raise ValueError("el intervalo entre marcas de tiempo es demasiado grande para representarlo")
    window_ratio = duration/window
    if not math.isfinite(window_ratio) or window_ratio > 200000:
        raise ValueError("el intervalo crearía más de 200000 ventanas de actividad; aumente --window o revise la entrada")
    window_count = math.floor(window_ratio + 1e-12) + 1
    bins=_aggregate(records, window, origin)
    outroot=output_root.resolve()
    data_dir=_safe_under(outroot,"data","processed",slug)
    fig_dir=_safe_under(outroot,"figures",slug)
    docs_dir=_safe_under(outroot,"docs","results")
    for p in (data_dir,fig_dir,docs_dir): p.mkdir(parents=True,exist_ok=True)
    with (data_dir/"activity.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["window_start_s","window_end_s","ul_prb_assignments","dl_prb_assignments","dci_records","observed_nonreserved_rnti_count"])
        for i in sorted(bins):
            b=bins[i]; w.writerow([f"{i*window:.6f}",f"{(i+1)*window:.6f}",b["ul_prb_assignments"],b["dl_prb_assignments"],b["dci_records"],b["observed_nonreserved_rnti_count"]])
    total_prb=sum(r.nof_prb for r in records)
    console_stats=_parse_console_stats(console_text or "")
    mcs_counts = _mcs_counts(records)
    with (data_dir/"mcs_distribution.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["mcs_idx","ul_dci_records","dl_dci_records"])
        for mcs in range(32): w.writerow([mcs,mcs_counts[0][mcs],mcs_counts[1][mcs]])
    summary={"session_label":label,"session_slug":slug,"frequency_mhz":frequency,"window_seconds":window,
             "valid_rows":counts["valid_rows"],"invalid_rows":counts["invalid_rows"],"schema_errors":counts["schema_errors"],
             "total_lines":counts["total_lines"],"comment_lines":counts["comment_lines"],"blank_lines":counts["blank_lines"],
             "first_timestamp":origin,"last_timestamp":last,"duration_seconds":duration,
             "sfn_note":"Se acepta SFN como contador no negativo; EyeCore puede incrementarlo más allá del rango LTE de 10 bits.",
             "dci_records":len(records),"total_prb_assignments":total_prb,
             "observed_nonreserved_rnti_count":len({r.rnti for r in records if 0<r.rnti<RESERVED_RNTI_MIN}),
             "rnti_count_note":"Solo identificadores no reservados observados (se excluyen RNTI 0 y valores >=65524); no representa todos los C-RNTI, dispositivos ni usuarios.",
             "activity_windows_with_records":len(bins)}
    if "skipped_subframes" in console_stats:
        summary["console_skipped_subframes_run_level"] = console_stats["skipped_subframes"]
    if "skipped_subframe_percent" in console_stats:
        summary["console_skipped_subframe_percent_run_level"] = console_stats["skipped_subframe_percent"]
    if duration < 120: summary["duration_warning"]="La captura abarca menos de 120 segundos; la duración se calcula con las marcas de tiempo válidas, no con el tiempo de ejecución solicitado."
    if len(records)<100: summary["record_count_warning"]="Hay menos de 100 registros DCI decodificados válidos; interprete los agregados con cautela."
    (data_dir/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    _write_svg(fig_dir/"activity.svg",bins,window,frequency)
    _write_mcs_svg(fig_dir/"mcs.svg",mcs_counts)
    # Synthetic record-removal sensitivity experiment. Independent fixed-seed stream per rate.
    exp=[]
    for loss in (0,10,30,50):
        rng=random.Random(42); kept=[r for r in records if rng.random() >= loss/100]
        total=sum(r.nof_prb for r in kept)
        exp.append({"synthetic_record_removal_percent":loss,"retained_records":len(kept),"total_prb_assignments":total,
                    "change_from_baseline_prb_assignments":total-total_prb,
                    "change_from_baseline_percent":(100*(total-total_prb)/total_prb if total_prb else 0.0)})
    with (data_dir/"synthetic_record_removal.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(exp[0])); w.writeheader(); w.writerows(exp)
    _write_loss_svg(fig_dir/"synthetic_record_removal.svg",exp)
    skipped=console_stats.get("skipped_subframes")
    lines=[f"# Sesión LTE FALCON: {slug}","",f"Resumen del registro DCI decodificado en **{frequency:g} MHz**.","",
           f"- Registros válidos: {len(records)}; filas no válidas: {counts['invalid_rows']} (errores de esquema: {counts['schema_errors']}).",
           f"- Intervalo de tiempo: {duration:.3f} segundos, desde {origin:.6f} hasta {last:.6f}.",
           f"- Asignaciones PRB observadas: {total_prb}; registros DCI: {len(records)}.",
           f"- RNTI no reservados distintos observados: {summary['observed_nonreserved_rnti_count']}. Se excluyen RNTI 0 y valores >=65524. La cifra es aproximada respecto al uso de identificadores reservados y no clasifica ni cuenta todos los C-RNTI, dispositivos o usuarios.","",
           "Los intervalos sin registros no aparecen en el CSV y se muestran como espacios en blanco en la gráfica. Las asignaciones PRB son concesiones observadas en registros decodificados; no representan utilización, caudal, congestión ni tráfico entregado.","",
           "## Gráficas y datos","",
           f"- Actividad: [activity.svg](../../figures/{slug}/activity.svg)",
           f"- Distribución MCS: [mcs.svg](../../figures/{slug}/mcs.svg). Los valores MCS cuentan registros decodificados y no miden directamente la calidad del canal.",
           f"- Agregados por intervalo: [activity.csv](../../data/processed/{slug}/activity.csv)",
           f"- Conteos MCS: [mcs_distribution.csv](../../data/processed/{slug}/mcs_distribution.csv)","",
           "## Experimento sintético de eliminación de registros","",
           "Un experimento de Bernoulli con semilla fija elimina registros decodificados en los porcentajes indicados y compara las asignaciones PRB totales con la base. Simula la pérdida de registros decodificados; no representa subtramas reales, un modelo de RF ni un detector de anomalías. Usa una sola semilla y sirve como exploración, no como estimación de precisión.",
           f"- [Gráfica de eliminación sintética](../../figures/{slug}/synthetic_record_removal.svg)",
           f"- [Valores de eliminación sintética](../../data/processed/{slug}/synthetic_record_removal.csv)","",
           "## Notas de captura","",f"El análisis contó {counts['comment_lines']} líneas de comentario y {counts['blank_lines']} líneas vacías."]
    if skipped is not None:
        lines.append(f"El resumen de consola informó {skipped} subtramas omitidas en toda la ejecución; no es un conteo por intervalo. El valor cero se conserva como estadística válida y no invalida la captura.")
        if "skipped_subframe_percent" in console_stats:
            lines.append(f"La consola también informó {console_stats['skipped_subframe_percent']:g}% de subtramas omitidas en toda la ejecución.")
    else: lines.append("No se proporcionó un resumen reconocido de subtramas omitidas en la consola.")
    if "duration_warning" in summary: lines.extend(["", "**Nota sobre la duración:** "+summary["duration_warning"]])
    if "record_count_warning" in summary: lines.extend(["", "**Nota sobre los registros:** "+summary["record_count_warning"]])
    (docs_dir/f"{slug}.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    summary["outputs"]={"summary":str(data_dir/"summary.json"),"activity_csv":str(data_dir/"activity.csv"),"activity_svg":str(fig_dir/"activity.svg"),"report":str(docs_dir/f"{slug}.md")}
    return summary


def _write_loss_svg(path: Path, rows: list[dict]):
    vals=[r["total_prb_assignments"] for r in rows]; mx=max(vals+[1]); pts=[]
    for r,v in zip(rows, vals):
        pts.append((100+750*r["synthetic_record_removal_percent"]/50,250-180*v/mx))
    poly=" ".join(f"{x},{y:.1f}" for x,y in pts)
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="330" viewBox="0 0 900 330"><rect width="100%" height="100%" fill="white"/>',
       '<style>text{font-family:Arial,sans-serif;fill:#182230}</style><text x="80" y="30" font-size="18" font-weight="bold">Sensibilidad a la eliminación sintética de registros decodificados</text>',
       '<line x1="80" y1="250" x2="850" y2="250" stroke="#425466"/><line x1="80" y1="55" x2="80" y2="250" stroke="#425466"/>',
       f'<polyline points="{poly}" fill="none" stroke="#7952a3" stroke-width="3"/>']
    for (x,y),r in zip(pts,rows):
        s.append(f'<circle cx="{x}" cy="{y:.1f}" r="5" fill="#7952a3"/><text x="{x}" y="272" text-anchor="middle" font-size="12">{r["synthetic_record_removal_percent"]}%</text><text x="{x}" y="{y-10:.1f}" text-anchor="middle" font-size="11">{r["total_prb_assignments"]}</text>')
    s.append('<text x="465" y="308" text-anchor="middle" font-size="12">Eliminación sintética de registros decodificados (%)</text><text transform="translate(22 160) rotate(-90)" text-anchor="middle" font-size="12">Asignaciones PRB totales conservadas</text></svg>')
    path.write_text("\n".join(s),encoding="utf-8")


def _parse_console_stats(text: str) -> dict:
    result = {}
    count_patterns=(r"(?:skipped\s+subframes|subframes\s+skipped)\s*[:=]\s*(\d+)",r"skipped\s*[:=]\s*(\d+)\s*subframes")
    for pat in count_patterns:
        m=re.search(pat,text,re.I)
        if m:
            result["skipped_subframes"] = int(m.group(1))
            break
    percent_patterns=(r"(?:skipped\s+subframes|subframes\s+skipped)[^\n%]*?([0-9]+(?:\.[0-9]+)?)\s*%",r"([0-9]+(?:\.[0-9]+)?)\s*%[^\n]*skipped\s+subframes")
    for pat in percent_patterns:
        m=re.search(pat,text,re.I)
        if m:
            result["skipped_subframe_percent"] = float(m.group(1))
            break
    return result


def _parse_console(text: str) -> int | None:
    return _parse_console_stats(text).get("skipped_subframes")


class SpanishArgumentParser(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage().replace("usage:", "uso:")

    def format_help(self):
        return super().format_help().replace("usage:", "uso:").replace("options:", "opciones:")

    def error(self, message):
        if message.startswith("the following arguments are required:"):
            message = "faltan los argumentos obligatorios:" + message.split(":", 1)[1]
        elif message.startswith("unrecognized arguments:"):
            message = "argumentos no reconocidos:" + message.split(":", 1)[1]
        elif "invalid float value:" in message:
            option = message.split(":", 1)[0]
            message = f"{option}: se esperaba un número decimal"
        elif "expected one argument" in message:
            option = message.split(":", 1)[0]
            message = f"{option}: falta un valor"
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    p=SpanishArgumentParser(description=__doc__, add_help=False)
    p.add_argument("-h", "--help", action="help", help="Mostrar este mensaje de ayuda y salir")
    p.add_argument("--input",required=True,type=Path,help="Archivo con registros DCI decodificados")
    p.add_argument("--session-label",required=True,help="Etiqueta para los archivos de salida")
    p.add_argument("--frequency-mhz",type=float,default=1970,help="Frecuencia en MHz (por defecto: 1970)")
    p.add_argument("--window",type=float,default=1,help="Duración de cada intervalo en segundos (por defecto: 1)")
    p.add_argument("--output-root",type=Path,default=Path("."),help="Carpeta raíz de los archivos generados (por defecto: carpeta actual)")
    p.add_argument("--console",type=Path,help="Archivo opcional con el resumen de consola")
    a=p.parse_args(argv)
    try:
        console=a.console.read_text(encoding="utf-8",errors="replace") if a.console else None
        s=analyze(a.input,a.session_label,a.frequency_mhz,a.window,a.output_root,console)
        print(json.dumps(s,indent=2,ensure_ascii=False))
        return 0
    except (OSError,ValueError) as e:
        print(f"analyze.py: error: {e}",file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
