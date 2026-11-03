"""Command line: python -m beyondsearch <command> --config configs/beauty_india.yaml

  merge     shared workbook -> data/processed/response_log.csv
  validate  check the inputs and print findings (exit code 1 if there is an error)
  run       validate + analyse + save everything (figures, tables, insight log, summary, manifest)
  profile   quick profile of any csv/xlsx file
  package   copy the latest outputs into deliverables/<name>/ as a frozen submission
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no screen needed: works on servers, Colab and laptops alike

from .config import Config
from .errors import BeyondSearchError, ConfigError
from .iotools import read_csv_checked, write_json

DEFAULT_CONFIG = "configs/beauty_india.yaml"


def _cfg(args) -> Config:
    return Config.load(args.config, root=args.root)


def cmd_merge(args) -> int:
    from .ingest import merge_workbook, write_response_log
    from .logsetup import setup_logging
    cfg = _cfg(args)
    logger = setup_logging("merge", None, args.verbose)
    wb = Path(args.workbook) if args.workbook else cfg.path("raw_workbook")
    df, info = merge_workbook(wb, cfg, logger)
    out = write_response_log(df, cfg)
    logger.info(f"wrote {out} ({len(df)} rows)")
    return 0


def cmd_validate(args) -> int:
    from .validate import validate_inputs
    cfg = _cfg(args)
    rl = read_csv_checked(cfg.path("response_log"), label="response_log")
    panel = read_csv_checked(cfg.path("prompt_panel"), label="prompt_panel")
    sched = read_csv_checked(cfg.path("run_schedule"), label="run_schedule")
    rep = validate_inputs(cfg, rl, panel, sched)
    for f in rep.findings:
        print(f"{f.level:5} [{f.check}] {f.message} ({f.count})")
    print("OK" if rep.ok else f"{len(rep.errors)} error(s)")
    return 0 if rep.ok else 1


def cmd_run(args) -> int:
    from .pipeline import run_pipeline
    cfg = _cfg(args)
    res, validation, rec = run_pipeline(cfg, out_dir=args.out, make_pdf=not args.no_pdf, verbose=args.verbose)
    print(f"\nDone. Results in {args.out or cfg.path('output_dir')} (open summary.html and run_report.md)")
    return 0


def cmd_profile(args) -> int:
    from .profile import profile_file
    print(profile_file(Path(args.file), Path(args.out) if args.out else None))
    return 0


def cmd_package(args) -> int:
    cfg = _cfg(args)
    src, dst = cfg.path("output_dir"), cfg.root / "deliverables" / args.name
    if not (src / "run_manifest.json").exists():
        raise ConfigError(f"No outputs in {src}. Run `python -m beyondsearch run` first.")
    dst.mkdir(parents=True, exist_ok=True)
    for item in ("insight_log.csv", "results.json", "summary.html", "summary.pdf", "run_manifest.json", "run_report.md"):
        if (src / item).exists():
            shutil.copyfile(src / item, dst / item)
    if (src / "figs").exists():
        shutil.copytree(src / "figs", dst / "figs", dirs_exist_ok=True)
    for nb in args.notebook or []:
        if Path(nb).exists():
            shutil.copyfile(nb, dst / Path(nb).name)
    write_json(dst / "PACKAGE.json", {"name": args.name, "from_run": __import__("json").loads((src / "run_manifest.json").read_text())["run_id"]})
    print(f"Packaged into {dst}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="beyondsearch", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=DEFAULT_CONFIG, help="YAML configuration (default: %(default)s)")
    ap.add_argument("--root", default=None, help="repository root if it is not the parent of the configs folder")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="command", required=True)
    m = sub.add_parser("merge"); m.add_argument("--workbook"); m.set_defaults(fn=cmd_merge)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    r = sub.add_parser("run"); r.add_argument("--out"); r.add_argument("--no-pdf", action="store_true"); r.set_defaults(fn=cmd_run)
    p = sub.add_parser("profile"); p.add_argument("file"); p.add_argument("--out"); p.set_defaults(fn=cmd_profile)
    k = sub.add_parser("package"); k.add_argument("--name", required=True); k.add_argument("--notebook", nargs="*"); k.set_defaults(fn=cmd_package)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2
    except BeyondSearchError as exc:
        print(f"DATA ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # unexpected: show a short message, keep the traceback out of the way unless -v
        if getattr(args, "verbose", False):
            raise
        print(f"UNEXPECTED ERROR ({type(exc).__name__}): {exc}\nRe-run with -v for the full traceback.", file=sys.stderr)
        return 3
