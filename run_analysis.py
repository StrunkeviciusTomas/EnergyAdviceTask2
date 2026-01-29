import os
import time
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SIX_MONTH_DAYS = 182


def _limit_to_last_6_months(df: pd.DataFrame, date_col: str = "data") -> pd.DataFrame:
    """Limit DataFrame rows to the last ~6 months based on the newest timestamp in `date_col`.

    Args:
        df: Input DataFrame.
        date_col: Column name containing datetimes.

    Returns:
        Filtered DataFrame (copy) containing only rows within the last ~6 months.
    """
    if df.empty or date_col not in df.columns:
        return df

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    max_dt = df[date_col].max()
    if pd.isna(max_dt):
        return df

    cutoff = max_dt - timedelta(days=SIX_MONTH_DAYS)
    return df[df[date_col] >= cutoff].copy()


def fetch_dataset(category: str, dataset_id: str, start_date: str, end_date: str):
    """Fetch dataset JSON from Litgrid Open API with simple retry logic.

    Args:
        category: API category path segment (e.g., 'gamyba', 'vartojimas').
        dataset_id: Dataset identifier in the API.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    Returns:
        Parsed JSON response (typically list of records). Returns [] on failure.
    """
    url = f"https://openapi.litgrid.eu/v1/kategorijos/{category}/{dataset_id}"
    params = {"nuo": start_date, "iki": end_date}

    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=120, verify=False)
            if response.status_code == 200:
                return response.json()
            print(f"  Bandymas {attempt + 1} nepavyko su statusu {response.status_code}")
        except Exception as e:
            print(f"  Bandymas {attempt + 1} nepavyko su klaida: {e}")
        time.sleep(5)

    return []


def fetch_all_data() -> pd.DataFrame:
    """Fetch all required datasets for the last ~6 months and merge into one DataFrame.

    Returns:
        DataFrame with a 'data' datetime column and one column per dataset.
        Returns empty DataFrame if nothing is fetched.
    """
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=SIX_MONTH_DAYS)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    datasets = {
        "101": "Kaupimo",
        "102": "Saules",
        "103": "Kitu",
        "104": "Siluminiu",
        "105": "Hidro",
        "106": "Vejo",
        "203": "Vartojimas",
    }

    all_dfs = []
    print(f"Nuskaitomi duomenys nuo {start_date} iki {end_date}...")

    for ds_id, name in datasets.items():
        cat = "gamyba" if ds_id.startswith("1") else "vartojimas"
        print(f"Nuskaitoma: {name} ({ds_id})...")
        data = fetch_dataset(cat, ds_id, start_date, end_date)

        if data:
            df = pd.DataFrame(data)
            if "ltu" in df.columns and "value" in df.columns:
                df = df[["ltu", "value"]].rename(columns={"value": name, "ltu": "data"})
                df["data"] = pd.to_datetime(df["data"])
                df = df.drop_duplicates(subset="data").set_index("data")
                all_dfs.append(df)
                print(f"  Gauta {len(df)} įrašų.")
            else:
                print(f"  Nenumatytos stulpelių antraštės: {df.columns}")
        else:
            print(f"  Duomenų negauta: {name}")

        time.sleep(1)

    if not all_dfs:
        return pd.DataFrame()

    final_df = pd.concat(all_dfs, axis=1, join="outer").sort_index().reset_index()
    final_df = _limit_to_last_6_months(final_df, "data")
    return final_df


def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process raw data: fill missing values, compute total generation and imbalance.

    Args:
        df: Input DataFrame containing 'data' and generation/consumption columns.

    Returns:
        Processed DataFrame with added columns: 'Sumine_Generacija', 'Disbalansas'.
    """
    if df.empty:
        print("Duomenų apdorojimas nutrauktas: DataFrame tuščias.")
        return df

    df = _limit_to_last_6_months(df, "data")
    sources = ["Kaupimo", "Saules", "Kitu", "Siluminiu", "Hidro", "Vejo"]

    df[sources] = df[sources].fillna(0)
    df["Vartojimas"] = df["Vartojimas"].ffill()

    df["Sumine_Generacija"] = df[sources].sum(axis=1)
    df["Disbalansas"] = df["Sumine_Generacija"] - df["Vartojimas"]

    return df


def create_visualizations(df: pd.DataFrame) -> None:
    """Create plots for the last ~6 months: generation vs consumption, imbalance, monthly pies.

    Args:
        df: Processed DataFrame with 'data', 'Sumine_Generacija', 'Vartojimas', 'Disbalansas'.

    Returns:
        None. Saves PNG files to the current directory.
    """
    if df.empty:
        print("Vizualizacijos nutrauktos: DataFrame tuščias.")
        return

    df = _limit_to_last_6_months(df, "data")

    plt.figure(figsize=(12, 6))
    plt.plot(df["data"], df["Sumine_Generacija"], label="Suminė generacija", alpha=0.7)
    plt.plot(df["data"], df["Vartojimas"], label="Vartojimas", alpha=0.7)
    plt.title("Elektros generacija ir vartojimas (paskutiniai 6 mėn.)")
    plt.xlabel("Data")
    plt.ylabel("MW")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("generacija_vartojimas.png")
    plt.close()
    print("Išsaugotas grafikas: generacija_vartojimas.png")

    plt.figure(figsize=(12, 6))
    plt.fill_between(
        df["data"],
        df["Disbalansas"],
        0,
        where=(df["Disbalansas"] >= 0),
        color="green",
        alpha=0.3,
        label="Perteklius",
    )
    plt.fill_between(
        df["data"],
        df["Disbalansas"],
        0,
        where=(df["Disbalansas"] < 0),
        color="red",
        alpha=0.3,
        label="Trūkumas",
    )
    plt.plot(df["data"], df["Disbalansas"], color="black", linewidth=0.5, alpha=0.5)
    plt.title("Elektros gamybos ir vartojimo disbalansas")
    plt.xlabel("Data")
    plt.ylabel("MW")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("disbalansas.png")
    plt.close()
    print("Išsaugotas grafikas: disbalansas.png")

    sources = ["Kaupimo", "Saules", "Kitu", "Siluminiu", "Hidro", "Vejo"]
    df["month"] = df["data"].dt.to_period("M")
    os.makedirs("pie_charts", exist_ok=True)

    for month in df["month"].unique():
        month_data = df[df["month"] == month]
        monthly_sums = month_data[sources].sum()
        monthly_sums = monthly_sums[monthly_sums > 0]

        if not monthly_sums.empty:
            plt.figure(figsize=(8, 8))
            plt.pie(monthly_sums, labels=monthly_sums.index, autopct="%1.1f%%", startangle=140)
            plt.title(f"Gamybos šaltinių pasiskirstymas - {month}")
            plt.tight_layout()
            plt.savefig(f"pie_charts/gamyba_{month}.png")
            plt.close()

    print("Išsaugoti mėnesio pyragų grafikai 'pie_charts' kataloge.")


def perform_analysis(df: pd.DataFrame) -> None:
    """Analyze hydro starts/hours, weekday consumption, and fit a polynomial weekly profile.

    Args:
        df: Processed DataFrame with 'data', 'Hidro', 'Vartojimas'.

    Returns:
        None. Saves 'vidutine_savaite.png' and 'analizes_rezultatai.txt'.
    """
    if df.empty:
        print("Analizė nutraukta: DataFrame tuščias.")
        return

    df = _limit_to_last_6_months(df, "data")

    df["hidro_active"] = df["Hidro"] > 0
    df["hidro_start"] = df["hidro_active"] & (~df["hidro_active"].shift(1).fillna(False))

    total_starts = int(df["hidro_start"].sum())
    total_hours = int(df["hidro_active"].sum())

    df["weekday"] = df["data"].dt.day_name()
    weekday_avg = df.groupby("weekday")["Vartojimas"].mean().sort_values(ascending=False)
    max_weekday = weekday_avg.index[0] if not weekday_avg.empty else "N/A"

    df["hour_of_week"] = df["data"].dt.dayofweek * 24 + df["data"].dt.hour
    avg_week = df.groupby("hour_of_week")["Vartojimas"].mean().reset_index()
    x = avg_week["hour_of_week"]
    y = avg_week["Vartojimas"]

    z = np.polyfit(x, y, 12)
    p = np.poly1d(z)

    plt.figure(figsize=(12, 6))
    plt.plot(x, y, label="Vidutinis vartojimas", color="blue", alpha=0.6)
    plt.plot(x, p(x), label="Polinominis fittas (deg=12)", color="red", linestyle="--")
    plt.title("Vidutinė elektros vartojimo savaitė ir polinominis modelis")
    plt.xlabel("Savaitės diena")
    plt.ylabel("MW")
    plt.legend()
    plt.grid(True)
    plt.xticks(range(0, 168, 24), ["Pr", "An", "Tr", "Kt", "Pn", "Še", "Se"])
    plt.tight_layout()
    plt.savefig("vidutine_savaite.png")
    plt.close()
    print("Išsaugotas grafikas: vidutine_savaite.png")

    report = f"""
Analizės ataskaita (paskutiniai 6 mėnesiai)
--------------------------------------------------

7) Hidroelektrinių analizė:
   - Pasileidimų skaičius: {total_starts}
   - Iš viso išdirbta laiko (valandomis): {total_hours}

8) Didžiausio vartojimo savaitės diena:
   - Diena su didžiausiu vidutiniu vartojimu: {max_weekday}
   - Vidutinis vartojimas pagal savaitės dienas (MW):
{weekday_avg.to_string()}

10) Polinomo koeficientai (12 laipsnio):
{z}
"""
    with open("analizes_rezultatai.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print("Išsaugota ataskaita: analizes_rezultatai.txt")


if __name__ == "__main__":
    print("Pradedama Litgrid duomenų analizė...")

    df = fetch_all_data()

    if not df.empty:
        df = process_data(df)

        df.to_csv("processed_litgrid_data.csv", index=False)
        print("Apdoroti duomenys išsaugoti: processed_litgrid_data.csv")

        create_visualizations(df)
        perform_analysis(df)

        print("\nAnalizė sėkmingai baigta. Visi failai sukurti dabartiniame kataloge.")
    else:
        print("\nAnalizė nepavyko: nepavyko nuskaityti duomenų.")
