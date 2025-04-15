# LinkExtractor Lite

## Setting-up

1. Clone and `cd` into repository
2. Create and activate a virtual environment
    ```
    python3 -m pip venv .venv
    source .venv/bin/activate
    ```
3. Install dependencies
    ```
    pip install -r requirements.txt
    ```
4. Run `python3 main.py` once to create and initialize `database.db`.

## Testing

At the moment, there are two entrypoints of the applciation for testing purposes:
1. `main.py`
   - This is a file that contains some test-strings with basic benchmarking for performance.
   - Simply run `python3 main.py`
2. `tests/`
   - This folder contains test-cases for various formulations of citations.
   - Run with `pytest`

## Scripts

- `preprocess.py`:
  - downloads the BWBIdList file and processes it accordingly to linkextractor.  