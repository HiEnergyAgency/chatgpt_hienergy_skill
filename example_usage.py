from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from hienergy_client import HiEnergyClient


def main() -> None:
    client = HiEnergyClient()
    advertisers = client.search_advertisers("supplements", limit=5)
    print(f"Found {len(advertisers)} advertisers")
    for advertiser in advertisers[:5]:
        print(
            f"- {advertiser.get('name', 'Unknown')} "
            f"({advertiser.get('domain', 'no-domain')})"
        )


if __name__ == "__main__":
    main()
