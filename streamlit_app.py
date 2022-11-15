import base64
from io import BytesIO
import streamlit as st
import logging
import sqlite3
from streamlit_folium import folium_static
import folium
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from math import radians, cos, sin, asin, sqrt, atan2, degrees
from PIL import Image


log = logging.getLogger("streamlit")
log.setLevel(logging.DEBUG)

WHITE = (255, 255, 255)


@st.experimental_memo
def get_rotated_arrow(degrees: float) -> str:
    img = Image.open("./arrow.png").convert("RGB").resize((50, 50))
    result = img.rotate(-degrees, fillcolor=WHITE)
    buffered = BytesIO()
    result.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def haversine(
    lat1: float, lon1: float, lat2: float, lon2: float, units: str = "km"
) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)

    src: https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points/4913653#4913653
    """
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # haversine formula
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1
    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371 if units == "km" else 3956  # Radius of earth in kilometers vs miles
    return c * r


def helper_haversine(row: pd.Series, target_lat: float, target_lon: float) -> float:
    row_lat, row_lon = row.centroid.y, row.centroid.x
    return haversine(row_lat, row_lon, target_lat, target_lon)


def get_flat_earth_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Flat-earther bearing

    For globe projected initial or final bearing: https://www.movable-type.co.uk/scripts/latlong.html
    # y = sin(lon2 - lon1) * cos(lat2)
    # x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(lon2 - lon1)
    # angle = atan2(x, y)
    # bearing = (degrees(angle) + 360) % 360  # in degrees
    """
    relative_lat = lat2 - lat1
    relative_lon = lon2 - lon1
    angle = atan2(relative_lon, relative_lat)

    return degrees(angle)


def helper_bearing(row: pd.Series, target_lat: float, target_lon: float) -> float:
    row_lat, row_lon = row.centroid.y, row.centroid.x
    return get_flat_earth_bearing(row_lat, row_lon, target_lat, target_lon)


MAX_DISTANCE = haversine(0, 0, 180, 0, "km")

@st.experimental_singleton
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(
        database="file:countries.db?immutable=1",
        timeout=5,
        detect_types=0,
        isolation_level="DEFERRED",
        check_same_thread=False,
        factory=sqlite3.Connection,
        cached_statements=128,
        uri=True,
    )
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    conn.load_extension("mod_spatialite")
    return conn


def get_random_location() -> sqlite3.Row:
    conn = get_connection()
    query = "SELECT * FROM country WHERE type != 'Dependency' and type != 'Lease' ORDER BY RANDOM() LIMIT 1;"
    cursor = conn.execute(query)
    result = cursor.fetchone()
    return result


@st.experimental_singleton
def get_all_locations() -> gpd.GeoDataFrame:
    conn = get_connection()
    query = f"SELECT *, Hex(ST_AsBinary(geometry)) as 'geom' FROM country WHERE type != 'Dependency' and type != 'Lease' ORDER BY name_en;"
    result = gpd.GeoDataFrame.from_postgis(query, conn, index_col="fid")
    result["area"] = result.area
    result["centroid"] = result.centroid
    result["lat"] = result.centroid.y
    result["lon"] = result.centroid.x
    return result


def get_distances(fid: int) -> gpd.GeoDataFrame:
    gdf = get_all_locations()
    result: gpd.GeoDataFrame = gdf.copy().set_crs("EPSG:4326")
    target_centroid = result.loc[fid, "centroid"]
    target_lat, target_lon = target_centroid.y, target_centroid.x
    result["distance"] = result.apply(
        helper_haversine, axis=1, args=(target_lat, target_lon)
    )
    result["direction"] = result.apply(
        helper_bearing, axis=1, args=(target_lat, target_lon)
    )
    return result


@st.experimental_memo
def get_country_names(all_locations: pd.DataFrame, locale_col: str = "name_en") -> list:
    names = all_locations[locale_col]
    return names.to_list()


def on_reset():
    st.session_state.pop(RANDOM_LOCATION)


def update_params():
    query_params = {LOCALE: st.session_state.get(LOCALE)}
    st.experimental_set_query_params(**query_params)


RANDOM_LOCATION = "random_location"
ALL_LOCATIONS = "all_locations"
NAMES = "names"
GUESSES = "guesses"
LOCALE = "locale"
DEFAULT_LOCALE = 'en'

def main():
    st.set_page_config(
        page_title="Spatial-lit Worldle",
        page_icon="🌍",
        initial_sidebar_state="collapsed",
        
    )
    st.title("Guess the Country 'Worldle' Edition! 🌍")
    st.markdown(
        "Heavily inspired by [Worldle](https://worldle.teuteuf.fr/) guessing game. Worldle is heavily inspired by [Wordle](https://www.nytimes.com/games/wordle/index.html)."
    )
    query_params = st.experimental_get_query_params()
    locale_index = 3
    try:
        query_locales = query_params.get(LOCALE)
        locale_list = list(LOCALES.keys())
        locale_index = locale_list.index(query_locales[0])
    except (ValueError, TypeError):
        pass

    selected_locale = st.sidebar.selectbox("Locale", LOCALES, locale_index, key=LOCALE, on_change=update_params)
    update_params()
    locale_col = LOCALES.get(selected_locale, "en")
    if RANDOM_LOCATION not in st.session_state:
        random_location = get_random_location()
        all_locations = get_distances(random_location["fid"])
        guesses = []
        st.session_state[RANDOM_LOCATION] = random_location
        st.session_state[ALL_LOCATIONS] = all_locations
        st.session_state[GUESSES] = guesses
    else:
        random_location = st.session_state.get(RANDOM_LOCATION)
        all_locations = st.session_state.get(ALL_LOCATIONS)
        guesses = st.session_state.get(GUESSES)

    already_won = random_location["fid"] in guesses
    target_centroid = all_locations.loc[[random_location["fid"]], "centroid"]
    target_lat, target_lon = all_locations.loc[random_location["fid"], ["lat", "lon"]]
    if already_won:
        st.balloons()
        st.success("You Guessed Correctly! 🥳")
        st.header(all_locations.loc[random_location["fid"], locale_col])
        target_gdf = all_locations.loc[guesses, "geom"]
        m = folium.Map(
            location=[target_lat, target_centroid.x],
            zoom_start=3,
        )
        target_gdf.explore(m=m)
        folium_static(m, width=725)
        st.button("Play Again!", on_click=on_reset)
        st.subheader("All Location Data")
        safe_cols = [col for col in all_locations.columns if all_locations[col].dtype != 'geometry']
        df = all_locations[safe_cols]
        st.dataframe(df)
        st.stop()

    with st.expander("What is This?"):
        st.write(
            """\
### Streamlit Worldle
A geography guessing game with the following rules:

- You are given the outline of a mystery Country or Territory 🌏
- If you guess the correct Country then you win 🥳
- If you guess incorrectly 6 times then you lose 😔
- Each incorrect guess will reveal information that might help you locate the mystery Country:
    - 📏 The `distance` that the center of the guess Country is away from the mystery Country
    - 🧭 The `direction` that points from the guess Country to the mystery Country (on a 2D map)
    - 🥈 The `proximity` percentage of how correct the guess was. A guess on the opposite side of the globe will be `0%` and the correct guess will be `100%`.

### Data Sources and Caveats

- World Bank: [World Boundaries GeoDatabase](https://datacatalog.worldbank.org/search/dataset/0038272/World-Bank-Official-Boundaries)
    - Provides Country and Territory shapes, locations, and names
    - Loaded into SQLite + Spatialite database (see original location guessing [repository on github](https://github.com/gerardrbentley/streamlit-location-guesser))
    - Some boundaries may not be precise or might include satellite territories in addition to mainland
- 📏 `distance` is the [Haversine Distance](https://en.wikipedia.org/wiki/Haversine_formula) calculated based on the [centroids](http://wiki.gis.com/wiki/index.php/Centroid) of the Countries calculated using GeoPandas
    - Countries that share a border will **NOT** have 0 km `distance`
    - The maximum `distance` possible is roughly `20000 km` (two points on opposite sides of the globe)
    - The `proximity` percentage is based on the maximum `distance`
"""
        )
        st.write("""Built with ❤️ by [Gerard Bentley](https://tech.gerardbentley.com/). Powered by Python 🐍 + Streamlit 🎈""")
    with st.expander("Hints! (Optional)", True):
        show_guesses_on_map = st.checkbox("Reveal your guesses on a map (will load an additional map below the mystery country)", False)
        show_on_map = st.checkbox("Reveal the mystery country on a map (will load a map centered on the mystery country", False)


    if not already_won and not show_on_map:
        fig, ax = plt.subplots(figsize=(3, 3))
        country = all_locations.loc[[random_location["fid"]]]
        country.plot(ax=ax, figsize=(0.5, 1), legend=True)
        ax.set_axis_off()
        st.pyplot(fig)

    guess_fid = None
    if show_guesses_on_map or show_on_map:
        targets = list(guesses)
        target_centroid = all_locations.loc[[random_location["fid"]], "centroid"]
        lat, lon = 0, 0

        if show_on_map:
            lat, lon = target_lat, target_lon
            targets.append(random_location["fid"])

        m = folium.Map(
            location=[lat, lon],
            zoom_start=3,
            tiles="Stamen Watercolor",
            attr="Stamen",
        )
        if len(targets):
            target_gdf = all_locations.loc[targets, "geom"]
            target_gdf.explore(m=m)
            for target in target_gdf:
                target_lat, target_lon = target.centroid.y, target.centroid.x
                folium.Marker(
                    [target_lat, target_lon], tooltip=f"{target_lat}, {target_lon}"
                ).add_to(m)
        folium_static(m, width=725)

    for display_guess in guesses:
        display_guess_country = all_locations.loc[display_guess]
        display_guess_name = display_guess_country[locale_col]
        distance = display_guess_country["distance"]
        distance_percentage = (1 - (distance / MAX_DISTANCE)) * 100
        direction = display_guess_country["direction"]

        arrow_image = get_rotated_arrow(direction)
        if int(distance_percentage) == 100:
            prox_icon = "🥇"
        elif int(distance_percentage) > 50:
            prox_icon = "🥈"
        else:
            prox_icon = "🥉"
        st.info(
            f"🌏 **{display_guess_name}** | 📏 **{distance:.0f}** km away | ![Direction {direction}](data:image/png;base64,{arrow_image}) | {prox_icon} **{distance_percentage:.2f}%**"
        )

    if len(guesses) == 6:
        st.error("You Guessed Incorrectly 6 Times 😔")
        st.button("Try Again!", on_click=on_reset)
        st.stop()

    with st.form("guess", True):
        guess = st.selectbox(
            "Guess the country (Click the drop down then type to filter)",
            all_locations[locale_col],
        )
        has_guessed = st.form_submit_button("Submit Guess!")

    st.button("Get new Random Country", on_click=on_reset)
    guess_fid = all_locations.index[all_locations[locale_col] == guess][0]

    if not has_guessed or guess_fid in guesses:
        st.warning("Submit a new Guess to continue!")
        st.stop()

    guesses.append(guess_fid)
    st.experimental_rerun()


LOCALES = {
    "ar": "name_ar",
    "bn": "name_bn",
    "de": "name_de",
    "en": "name_en",
    "es": "name_es",
    "fr": "name_fr",
    "el": "name_el",
    "hi": "name_hi",
    "hu": "name_hu",
    "id": "name_id",
    "it": "name_it",
    "ja": "name_ja",
    "ko": "name_ko",
    "nl": "name_nl",
    "pl": "name_pl",
    "pt": "name_pt",
    "ru": "name_ru",
    "sv": "name_sv",
    "tr": "name_tr",
    "vi": "name_vi",
    "zh": "name_zh",
}

if __name__ == "__main__":
    main()
