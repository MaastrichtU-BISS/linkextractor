# LinkExtractor Lite

The technical implementation details can be found in [ARCHITECTURE.md](ARCHITECTURE.md)

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
4. Run `python3 main.py` to view help and options

### Options

**Main**
- `eval`
    - **description**: used to scan strings for links
    - **options**:
        - `-e/--exact`: exact search

**Development commands**
- `test`
    - **description**: used to test predefined strings for scanning links and its performance
- `analyze`:
    - **description**: analyze the correctness of the link-scanning by comparing to lido results (for development and optimization purposes)
    - **options**:
        - `-p/--prepare`: prepare the samples
        - `-n/--samples`: amount of samples to prepare (to be used in conjunction with -p)
        - `-s/--seed`: seed for random generator of lido-entries to compare against (to be used in conjunction with -p)
        - `-c/--cherry-pick`: cherry pick eclis to download to analyze
        - `-2`: use the alternative mode for analysis, as defined in method_2.py
        

## Testing

At the moment, there are two entrypoints of the applciation for testing purposes:
1. `python3 main.py test`
   - Executing login on test-strings with basic benchmarking for performance.
   - Simply run `python3 main.py test`
2. `tests/`
   - This folder contains test-cases for various formulations of citations.
   - Run with `pytest`

## Data

For retrieving the appropriate data, [this DAG](https://github.com/maastrichtlawtech/case-law-explorer/tree/etl-lido/airflow/dags/lido) needs to be ran to populate the Postgres (and SQLite) database.
