"""
App Streamlit: Medidor y analizador de ondas de sonido.

Características:
- Subir archivo de audio (WAV/MP3).
- Reproducir audio dentro de la app.
- Mostrar forma de onda (time domain).
- Calcular FFT y mostrar espectro (frequency domain).
- Calcular frecuencia dominante, RMS y nivel en dB.
- Exportar informe (CSV/JSON) y descargar datos de la forma de onda.
- Integración ligera con Streamlit.py: guarda el último análisis en st.session_state['last_sound']
  para que otra app (por ejemplo Streamlit.py) la use si se ejecutan en la misma sesión.

Dependencias:
pip install streamlit numpy scipy soundfile matplotlib pandas

Nota: Para captura en vivo desde el micrófono hay componentes adicionales (streamlit-webrtc o componentes JS).
Aquí se usa carga de archivo (upload) para mantener la app simple y confiable.
"""

import io
import json
import numpy as np
import pandas as pd
import soundfile as sf
import matplotlib.pyplot as plt
from scipy import signal
import streamlit as st

st.set_page_config(page_title="Medidor de ondas de sonido", layout="wide")

st.title("Medidor y analizador de ondas de sonido")
st.write(
    "Sube un archivo de audio (WAV/MP3/FLAC) para visualizar la forma de onda, el espectro "
    "y obtener métricas (frecuencia dominante, RMS, dB)."
)

col_left, col_right = st.columns([2, 1])

with col_right:
    st.header("Opciones")
    # Mostrar integración con la app de álgebra si existe
    if "last_problem" in st.session_state:
        st.subheader("Integración con Generador de Álgebra")
        st.write("Último problema (desde Streamlit.py):")
        st.json(st.session_state["last_problem"])
        st.markdown("---")
    upload = st.file_uploader(
        "Subir archivo de audio", type=["wav", "mp3", "flac", "ogg", "aiff"], accept_multiple_files=False
    )
    apply_filter = st.checkbox("Aplicar ventana y filtro de suavizado al espectro", value=True)
    export_csv = st.checkbox("Permitir exportar datos de forma de onda (CSV)", value=True)
    export_json = st.checkbox("Generar informe JSON con métricas", value=True)

with col_left:
    if not upload:
        st.info("Sube un archivo de audio para empezar (por ejemplo, una grabación desde tu teléfono).")
        st.caption("Si necesitas captura desde el micrófono en vivo, puedo añadir soporte con streamlit-webrtc.")
    else:
        try:
            # Leer bytes y usar soundfile para obtener señal y sample rate
            data_bytes = upload.read()
            data_buffer = io.BytesIO(data_bytes)
            signal_data, sr = sf.read(data_buffer, dtype='float32')
            # soundfile devuelve (samples, channels) o (samples,)
            if signal_data.ndim > 1:
                # convertir a mono promedio de canales
                signal_mono = np.mean(signal_data, axis=1)
            else:
                signal_mono = signal_data

            N = len(signal_mono)
            duration = N / float(sr)
            time = np.linspace(0, duration, N, endpoint=False)

            # Normalizar (ya está en float32 típicamente)
            max_abs = np.max(np.abs(signal_mono)) if N > 0 else 1.0
            if max_abs == 0:
                normalized = signal_mono
            else:
                normalized = signal_mono / max_abs

            # Métricas
            rms = np.sqrt(np.mean(signal_mono.astype(np.float64) ** 2))
            # evitar log(0)
            eps = 1e-12
            db = 20 * np.log10(rms + eps)

            # FFT
            # aplicamos ventana Hann para reducir leakage
            window = np.hanning(N)
            windowed = signal_mono * window
            # usar rfft
            freqs = np.fft.rfftfreq(N, d=1.0 / sr)
            fft_vals = np.fft.rfft(windowed)
            mag = np.abs(fft_vals)

            if apply_filter:
                # suavizado simple del espectro (filtro mediana)
                mag_smoothed = signal.medfilt(mag, kernel_size=5)
                mag_display = mag_smoothed
            else:
                mag_display = mag

            # encontrar frecuencia dominante (ignorando DC)
            if len(freqs) > 1:
                idx_peak = np.argmax(mag_display[1:]) + 1
                dominant_freq = freqs[idx_peak]
            else:
                dominant_freq = 0.0

            # Mostrar reproductor
            st.subheader("Reproducir audio")
            st.audio(data_bytes, format=upload.type)

            st.subheader("Información del archivo")
            st.write(f"Nombre: {upload.name}")
            st.write(f"Duración: {duration:.3f} s")
            st.write(f"Tasa de muestreo: {sr} Hz")
            st.write(f"Muestras: {N}")
            st.write(f"RMS: {rms:.6f}")
            st.write(f"Nivel aproximado (dBFS): {db:.2f} dB")
            st.write(f"Frecuencia dominante (estimada): {dominant_freq:.2f} Hz")

            st.markdown("---")
            # Plot forma de onda
            st.subheader("Forma de onda (time domain)")
            fig_wf, ax_wf = plt.subplots(figsize=(10, 3))
            ax_wf.plot(time, normalized, color="#2b8cbe", linewidth=0.6)
            ax_wf.set_xlabel("Tiempo (s)")
            ax_wf.set_ylabel("Amplitud (normalizada)")
            ax_wf.set_xlim(0, min(duration, 10.0))  # mostrar hasta 10s por defecto
            ax_wf.grid(alpha=0.3)
            st.pyplot(fig_wf)
            plt.close(fig_wf)

            st.subheader("Espectro (frequency domain)")
            fig_sp, ax_sp = plt.subplots(figsize=(10, 3))
            # limitar eje x a Nyquist
            nyq = sr / 2.0
            # mostrar hasta 5 kHz por defecto o Nyquist si menor
            max_plot_freq = min(5000, nyq)
            mask = freqs <= max_plot_freq
            ax_sp.semilogy(freqs[mask], mag_display[mask] + eps, color="#e34a33")
            ax_sp.set_xlabel("Frecuencia (Hz)")
            ax_sp.set_ylabel("Magnitud (log)")
            ax_sp.grid(alpha=0.3)
            st.pyplot(fig_sp)
            plt.close(fig_sp)

            # Preparar datos exportables
            if export_csv:
                csv_df = pd.DataFrame({"time_s": time, "amplitude": signal_mono})
                csv_bytes = csv_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Descargar forma de onda (CSV)",
                    data=csv_bytes,
                    file_name=f"{upload.name}_waveform.csv",
                    mime="text/csv",
                )

            if export_json:
                report = {
                    "file_name": upload.name,
                    "duration_s": float(duration),
                    "sample_rate": int(sr),
                    "samples": int(N),
                    "rms": float(rms),
                    "db": float(db),
                    "dominant_freq_hz": float(dominant_freq),
                }
                report_bytes = json.dumps(report, indent=2).encode("utf-8")
                st.download_button(
                    label="Descargar informe (JSON)",
                    data=report_bytes,
                    file_name=f"{upload.name}_report.json",
                    mime="application/json",
                )

            # Guardar en session_state para integración con otras apps
            st.session_state["last_sound"] = {
                "file_name": upload.name,
                "duration_s": float(duration),
                "sample_rate": int(sr),
                "samples": int(N),
                "rms": float(rms),
                "db": float(db),
                "dominant_freq_hz": float(dominant_freq),
            }

            st.success("Análisis completado y guardado en session_state['last_sound'].")

        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")
            st.error(f"Error al resolver: {e}")

st.markdown("---")
st.write("Sugerencias: puedes ampliar esta app para generar listas de ejercicios, exportar a CSV/PDF, o añadir tipos adicionales (sistemas, factorización, inecuaciones).")
