# Streamlit Worldle

Streamlit + SQLite clone of worldle

Built with ❤️ by [gerardrbentley](https://github.com/gerardrbentley)

## What's this?

- `README.md`: This Document! To help you find your way around
- `streamlit_app.py`: The main app that gets run by [`streamlit`](https://docs.streamlit.io/)
- `requirements.txt`: Pins the version of packages needed
- `LICENSE`: Follows Streamlit's use of Apache 2.0 Open Source License
- `.gitignore`: Tells git to avoid comitting / scanning certain local-specific files
- `.streamlit/config.toml`: Customizes the behaviour of streamlit without specifying command line arguments (`streamlit config show`)

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

## Local Setup

Assumes working python installation and some command line knowledge ([install python with conda guide](https://tech.gerardbentley.com/python/beginner/2022/01/29/install-python.html)).

```sh
# External users: download Files
git clone git@github.com:gerardrbentley/streamlit_worldle.git

# Go to correct directory
cd streamlit_worldle

# Create virtual environment for this project
python -m venv venv

# Activate the virtual environment
. ./venv/bin/activate
# .\venv\Scripts\activate for Windows

# Install required Packages
python -m pip install -r requirements.txt

# Run the streamlit app
streamlit run streamlit_app.py
```

Open your browser to [http://localhost:8501/](http://localhost:8501/) if it doesn't open automatically.
## Deploy

For the easiest experience, deploy to [Streamlit Cloud](https://streamlit.io/cloud)

For other options, see [Streamilt deployment wiki](https://discuss.streamlit.io/t/streamlit-deployment-guide-wiki/5099)

## Credits

This package was created with Cookiecutter and the `gerardrbentley/cookiecutter-streamlit` project template.

- Cookiecutter: [https://github.com/audreyr/cookiecutter](https://github.com/audreyr/cookiecutter)
- `gerardrbentley/cookiecutter-streamlit`: [https://github.com/gerardrbentley/cookiecutter-streamlit](https://github.com/gerardrbentley/cookiecutter-streamlit)
