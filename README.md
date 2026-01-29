# Litgrid Electricity Data Analysis Tool

This project is a Python-based tool that fetches, processes, and analyzes electricity generation and consumption data from the **Litgrid Open API**. It focuses on the last 6 months of data to provide insights into Lithuania's energy balance.

## Features

* **Automated Data Fetching:** Retrieves data for Consumption, Solar, Wind, Hydro, Thermal, Storage, and "Other" generation sources.
* **Data Processing:** Merges multiple datasets, handles missing values, and calculates total generation vs. consumption imbalance.
* **Visualization:**
    * Time-series plots for Generation vs. Consumption.
    * Area charts showing Energy Surplus vs. Deficit.
    * Monthly Pie charts for generation mix.
    * Polynomial fitting (12th degree) for average weekly consumption profiles.
* **Statistical Analysis:** Calculates Hydro plant start-ups, total uptime, and identifies peak consumption days.

## Prerequisites

* Python 3.8 or higher.
* Internet connection (to access the Litgrid API).

## Installation

1.  **Clone or Download** this repository (or save the script as `main.py`).

2.  **Set up a Virtual Environment** (Recommended):
    It is best practice to run Python projects in a virtual environment to avoid dependency conflicts.

    * **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    * **macOS / Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    You need to install the required Python libraries. You can install them manually using `pip`.

    ```bash
    pip install pandas matplotlib numpy requests
    ```

    *Note: `urllib3` is usually installed automatically with requests, but if you encounter issues, install it explicitly: `pip install urllib3`.*

## Usage

1.  Ensure your virtual environment is active.
2.  Run the script using Python:

    ```bash
    python run_analysis.py
    ```

## Output

After the script finishes running, the following files will be generated in your project directory:

### Data Files
* `processed_litgrid_data.csv`: A CSV file containing the cleaned, merged dataset used for the analysis.
* `analizes_rezultatai.txt`: A text report containing:
    * Hydroelectric stats (start-ups and active hours).
    * Weekday consumption analysis.
    * Polynomial coefficients.

### Visualizations
* `generacija_vartojimas.png`: A line graph comparing total generation against consumption.
* `disbalansas.png`: A visual representation of energy surplus (green) and deficit (red).
* `vidutine_savaite.png`: A plot showing the average weekly consumption profile overlaid with a polynomial model.
* `pie_charts/`: A folder containing monthly breakdowns of energy generation sources (e.g., `gamyba_2025-07.png`).

## License

This project is for educational and analytical purposes using public data from Litgrid.