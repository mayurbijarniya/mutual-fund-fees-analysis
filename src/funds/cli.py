"""funds: download, ingest, build, analyze.

funds download   fetch the SEC files (needs --user-agent "Name email")
funds ingest     filter the quarterly zips and yearly fund lists to Parquet
funds build      build the dbt warehouse and run every data test
funds analyze    answer Q1-Q4, write results, figures, Tableau tables, findings
funds all        ingest, build and analyze, in order
"""

from __future__ import annotations

import argparse

from funds import paths

STEPS = ["download", "ingest", "build", "analyze", "all"]


def download(user_agent: str | None) -> None:
    from funds import download as fetch

    if not user_agent:
        raise SystemExit('funds download needs --user-agent "Your Name your@email.com"')
    names = fetch.run(user_agent)
    print(f"{len(names)} files in {paths.RAW}")


def ingest() -> None:
    from funds import ingest as convert

    converted = convert.run()
    classes = convert.lookups()
    print(f"converted {len(converted)} new quarters; {classes:,} fund list rows")


def build() -> None:
    from funds import build as dbt

    dbt.run("build")


def analyze() -> None:
    from funds import db, figures, report, run

    con = db.connect()
    output = run.analyze(con)
    con.close()
    saved = run.write(output)
    figures.render(output)
    report.render(saved)
    print(f"wrote {paths.RESULTS}, {paths.TABLEAU}/, {paths.FIGURES}/, {paths.FINDINGS}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="funds", description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=STEPS)
    parser.add_argument("--user-agent", help='SEC contact header, e.g. "Jane Doe jane@x.com"')
    args = parser.parse_args(argv)

    if args.step == "download":
        download(args.user_agent)
        return
    for step in ["ingest", "build", "analyze"] if args.step == "all" else [args.step]:
        {"ingest": ingest, "build": build, "analyze": analyze}[step]()


if __name__ == "__main__":
    main()
