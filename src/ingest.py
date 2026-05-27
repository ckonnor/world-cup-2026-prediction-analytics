from __future__ import annotations

from world_cup.io import check_required_raw_files, load_group_fixtures, load_knockout_slots


def main() -> None:
    missing = check_required_raw_files()
    if missing:
        print("Missing required raw files:")
        for path in missing:
            print(f"- {path}")
        raise SystemExit(1)

    group_fixtures = load_group_fixtures()
    knockout_slots = load_knockout_slots()

    print("Raw files found.")
    print(f"group_fixtures rows: {len(group_fixtures):,}")
    print(f"knockout_slots rows: {len(knockout_slots):,}")


if __name__ == "__main__":
    main()
