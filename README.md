# FTL: MV Choice Info
Concept from LoudMute, Made by ranhai

This mod shows you event info for each choice in events and fight(crew kill, hull kill, and surrender). This is useful for players wanting to learn the possible results of ingame events. It is also useful for players wanting to play optimally without having to refer to the wiki or XML diving.

## Running the script

Download MV data.zip and extract data/ into src-en/ at this directory(so it should be src-en/data/)

You can find scritps it in `scripts/`.

The scripts are written in Python3.11 and managed by poetry. To install poetry, just enter `pip install poetry`. And you can install dependencies by `poetry install`.

To make packages, run `python scripts/package.py`. After the packaging process, you will see the mod in `packages/`.

If you want to tune params for each event, edit value of class field `priority` in `scripts/events.py`.
