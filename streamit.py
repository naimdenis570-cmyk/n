import streamlit as st
from PIL import Image
import requests
from io import BytesIO

st.set_page_config(page_title="Transporte por Peso", layout="centered")

st.title("🚚 Selector de Transporte por Peso")
st.write("Ingresa el peso del objeto y verás qué tipo de transporte necesitas")

# Input del peso
weight = st.number_input("Peso del objeto (kg)", min_value=0.1, value=10.0, step=0.5)

# Definir categorías y sus imágenes
transport_options = {
    "Mano": {
        "min": 0,
        "max": 5,
        "description": "El objeto puede ser transportado a mano",
        "emoji": "🚶",
        "image_url": "https://via.placeholder.com/400x300?text=Transporte+a+Mano"
    },
    "Bicicleta": {
        "min": 5,
        "max": 25,
        "description": "El objeto puede ser transportado en bicicleta",
        "emoji": "🚴",
        "image_url": "https://via.placeholder.com/400x300?text=Bicicleta"
    },
    "Motocicleta": {
        "min": 25,
        "max": 100,
        "description": "El objeto requiere transporte en motocicleta",
        "emoji": "🏍️",
        "image_url": "https://via.placeholder.com/400x300?text=Motocicleta"
    },
    "Auto": {
        "min": 100,
        "max": 1000,
        "description": "El objeto requiere transporte en auto",
        "emoji": "🚗",
        "image_url": "https://via.placeholder.com/400x300?text=Auto"
    },
    "Camión": {
        "min": 1000,
        "max": 5000,
        "description": "El objeto requiere transporte en camión",
        "emoji": "🚚",
        "image_url": "https://via.placeholder.com/400x300?text=Camion"
    },
    "Camión grande": {
        "min": 5000,
        "max": float('inf'),
        "description": "El objeto requiere un camión de carga pesada",
        "emoji": "🚛",
        "image_url": "https://via.placeholder.com/400x300?text=Camion+Grande"
    }
}

# Encontrar el transporte adecuado
selected_transport = None
for transport, specs in transport_options.items():
    if specs["min"] <= weight < specs["max"]:
        selected_transport = transport
        break

if selected_transport:
    specs = transport_options[selected_transport]
    
    # Mostrar resultado
    st.success(f"{specs['emoji']} **Transporte recomendado: {selected_transport}**")
    st.info(specs["description"])
    
    # Mostrar la imagen
    st.subheader("Tipo de transporte:")
    try:
        response = requests.get(specs["image_url"])
        img = Image.open(BytesIO(response.content))
        st.image(img, use_column_width=True)
    except:
        st.image(specs["image_url"], use_column_width=True)
    
    # Información adicional
    st.write(f"**Peso ingresado:** {weight} kg")
    st.write(f"**Rango recomendado:** {specs['min']} - {specs['max']} kg")
else:
    st.warning("Peso fuera de rango")

# Tabla de referencia
st.divider()
st.subheader("📊 Tabla de referencias")

reference_data = []
for transport, specs in transport_options.items():
    max_weight = specs["max"] if specs["max"] != float('inf') else "Ilimitado"
    reference_data.append({
        "Transporte": f"{specs['emoji']} {transport}",
        "Peso mínimo (kg)": specs["min"],
        "Peso máximo (kg)": max_weight
    })

st.table(reference_data)
