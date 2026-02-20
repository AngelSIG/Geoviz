import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import io

# Configuration de la page
st.set_page_config(
    page_title="GeoViz App",
    page_icon=":world_map:",
    layout="wide"
)

# Titre
st.title(":world_map: Application de Visualisation Geospatiale")
st.markdown("""
Cette application vous permet de visualiser des points GPS
sur une carte interactive. Uploadez un fichier CSV contenant des colonnes 'latitude' et 'longitude'.
""")

# Sidebar pour les controles
with st.sidebar:
    st.header("Parametres")

    # Upload du fichier
    uploaded_file = st.file_uploader(
        "Choisissez un fichier CSV",
        type=["csv"]
    )

    # Type de visualisation
    viz_type = st.selectbox(
        "Type de visualisation",
        ["Marqueurs", "Clusters", "Heatmap"]
    )

    # Couleur des marqueurs
    marker_color = st.color_picker(
        "Couleur des marqueurs",
        "#33FFFC"
    )
    
    # --- BONUS 1: Filtre par colonne catégorielle ---
    st.subheader("Filtres avancés")
    enable_category_filter = st.checkbox("Ajouter un filtre catégorique", value=False)
    category_column = None
    category_filter = None
    
    # --- BONUS 3: Buffer zones ---
    st.subheader("Zones tampons (Buffers)")
    enable_buffer = st.checkbox("Afficher les zones tampons", value=False)
    buffer_size = st.slider(
        "Rayon du buffer (km)",
        min_value=0.1,
        max_value=10.0,
        value=1.0,
        step=0.1,
        disabled=not enable_buffer
    )
    
    # --- BONUS 4: Géocodage ---
    st.subheader("Géocodage")
    geocode_address = st.text_input("Convertir une adresse en coordonnées (optionnel)")
    if geocode_address:
        try:
            geolocator = Nominatim(user_agent="geoviz_app")
            location = geolocator.geocode(geocode_address, timeout=10)
            if location:
                st.success(f"Adresse trouvée: {location.latitude:.4f}, {location.longitude:.4f}")
                st.info(f"Cliquez pour copier: {location.latitude}, {location.longitude}")
            else:
                st.warning("Adresse non trouvée")
        except Exception as e:
            st.warning(f"Erreur géocodage: {e}")

# Contenu principal
if uploaded_file is not None:
    # Lecture des donnees
    try:
        df = pd.read_csv(uploaded_file)

        # Verification des colonnes requises
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            st.error("Le fichier doit contenir les colonnes 'latitude' et 'longitude'")
            st.stop()

        # --- BONUS 1: Créer le filtre catégorique ---
        if enable_category_filter:
            # Détecter les colonnes catégoriques
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            if categorical_cols:
                category_column = st.sidebar.selectbox(
                    "Colonne de filtre",
                    categorical_cols
                )
                unique_values = df[category_column].unique()
                category_filter = st.sidebar.multiselect(
                    f"Valeurs de {category_column}",
                    unique_values,
                    default=list(unique_values)[:3] if len(unique_values) > 3 else unique_values
                )
                # Appliquer le filtre
                df = df[df[category_column].isin(category_filter)]
            else:
                st.sidebar.warning("Aucune colonne catégorique trouvée")

        # Afficher un apercu
        st.subheader("Apercu des donnees")
        st.dataframe(df.head(10))

        # Statistiques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre de points", len(df))
        with col2:
            st.metric("Latitude moyenne", f"{df.latitude.mean():.4f}")
        with col3:
            st.metric("Longitude moyenne", f"{df.longitude.mean():.4f}")

        # Creation de la carte
        st.subheader("Carte interactive")

        # Centre sur la moyenne des points
        center_lat = df.latitude.mean()
        center_lon = df.longitude.mean()

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles="CartoDB positron"
        )

        # Ajout des donnees selon le type de visualisation
        if viz_type == "Marqueurs":
            for idx, row in df.iterrows():
                popup_text = row.get('Nom', f'Point {idx}')
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=6,
                    color=marker_color,
                    fill=True,
                    popup=str(popup_text)
                ).add_to(m)
                
                # --- BONUS 3: Ajouter les buffers ---
                if enable_buffer:
                    # Créer un buffer circulaire (approximation avec cercle)
                    folium.Circle(
                        location=[row['latitude'], row['longitude']],
                        radius=buffer_size * 1000,  # Convertir km en mètres
                        color='blue',
                        fill=True,
                        fillColor='blue',
                        fillOpacity=0.1,
                        weight=2,
                        popup=f"Buffer {buffer_size}km"
                    ).add_to(m)

        elif viz_type == "Clusters":
            marker_cluster = MarkerCluster().add_to(m)
            for idx, row in df.iterrows():
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=row.get('Nom', f'Point {idx}')
                ).add_to(marker_cluster)
                
                # --- BONUS 3: Ajouter les buffers aux clusters ---
                if enable_buffer:
                    folium.Circle(
                        location=[row['latitude'], row['longitude']],
                        radius=buffer_size * 1000,
                        color='blue',
                        fill=True,
                        fillColor='blue',
                        fillOpacity=0.1,
                        weight=2,
                        popup=f"Buffer {buffer_size}km"
                    ).add_to(m)

        elif viz_type == "Heatmap":
            heat_data = df[['latitude', 'longitude']].values.tolist()
            HeatMap(heat_data, radius=15).add_to(m)
            
            # --- BONUS 3: Ajouter les buffers à la heatmap ---
            if enable_buffer:
                for idx, row in df.iterrows():
                    folium.Circle(
                        location=[row['latitude'], row['longitude']],
                        radius=buffer_size * 1000,
                        color='blue',
                        fill=True,
                        fillColor='blue',
                        fillOpacity=0.05,
                        weight=1,
                        popup=f"Buffer {buffer_size}km"
                    ).add_to(m)

        # Affichage de la carte
        st_data = st_folium(m, width=None, height=500)
        
        # --- BONUS 2: Téléchargement de la carte en HTML ---
        st.subheader("Télécharger la carte")
        html_string = m._repr_html_()
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Télécharger la carte (HTML)",
                data=html_string,
                file_name="carte_interactive.html",
                mime="text/html"
            )
        
        with col2:
            # Bonus: Télécharger les données filtrées
            csv = df.to_csv(index=False)
            st.download_button(
                label="Télécharger les données (CSV)",
                data=csv,
                file_name="donnees_filtrees.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Erreur: {e}")

else:
    # Message d’accueil si pas de fichier
    st.info("Veuillez uploader un fichier CSV pour commencer.")
    
    # Exemple de format attendu
    st.subheader("Format attendu du fichier CSV")
    exemple = pd.DataFrame({
        'Nom': ['Forage A', 'Forage B', 'Forage C'],
        'latitude': [6.4969, 6.3654, 9.3370],
        'longitude': [2.6289, 2.4183, 2.6303]
    })
    st.dataframe(exemple)