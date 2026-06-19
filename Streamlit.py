"""
App Streamlit: Medidor y analizador de ondas de sonido.

Características:
- Subir archivo de audio (WAV/MP3/FLAC).
- Reproducir audio dentro de la app.
- Mostrar forma de onda (time domain).
- Calcular FFT y mostrar espectro (frequency domain).
- Calcular frecuencia dominante, RMS y nivel en dB.
- Exportar informe (CSV/JSON) y descargar datos de la forma de onda.
- Integración ligera con Streamlit.py: guarda el último análisis en st.session_state['last_sound']
  para que otra app (por ejemplo Streamlit.py) la use si se ejecuten en la misma sesión.

Dependencias:
pip install streamlit numpy scipy soundfile matplotlib pandas

Nota: Para captura en vivo desde el micrófono hay componentes adicionales (streamlit-webrtc o componentes JS).
Aquí se usa carga de archivo (upload) para mantener la app simple y confiable.
"""

import io
import json
import tempfile
import numpy as np
import pandas as pd
# Intentamos cargar matplotlib pero toleramos su ausencia
HAS_MPL = True
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None
    HAS_MPL = False

# Intentamos cargar scipy.signal, pero si no está disponible añadimos un fallback para medfilt
_HAS_SCIPY_SIGNAL = True
try:
    from scipy import signal
except Exception:
    signal = None
    _HAS_SCIPY_SIGNAL = False

from scipy.io import wavfile as scipy_wavfile
import streamlit as st

# Intentar importar soundfile (pysoundfile). Si no está disponible, usaremos un fallback con scipy (solo WAV).
HAS_SOUNDFILE = True
try:
    import soundfile as sf
except Exception:
    sf = None
    HAS_SOUNDFILE = False


def _medfilt_fallback(x, kernel_size=3):
    """Fallback sencillo para medfilt (solo 1D).
    No es tan eficiente como scipy.signal.medfilt pero evita errores si scipy no está presente."""
    x = np.asarray(x)
    if kernel_size <= 1 or x.size == 0:
        return x
    k = int(kernel_size)
    pad = k // 2
    x_padded = np.pad(x, pad, mode='edge')
    out = np.empty_like(x, dtype=x.dtype)
    for i in range(len(x)):
        window = x_padded[i : i + k]
        out[i] = np.median(window)
    return out


def safe_medfilt(x, kernel_size=3):
    if _HAS_SCIPY_SIGNAL and hasattr(signal, 'medfilt'):
        return signal.medfilt(x, kernel_size=kernel_size)
    else:
        return _medfilt_fallback(x, kernel_size=kernel_size)


def read_audio(data_bytes, filename_hint=None):
    """Leer audio desde bytes. Retorna (signal_data, sample_rate).

    - Si pysoundfile está disponible lo usará (soporta WAV/MP3/FLAC si libs del sistema están instaladas).
    - Si no, intentará usar scipy.io.wavfile leyendo a un archivo temporal (solo WAV).
    """
    if HAS_SOUNDFILE and sf is not None:
        data_buffer = io.BytesIO(data_bytes)
        # soundfile devuelve (samples, samplerate)
        signal_data, sr = sf.read(data_buffer, dtype='float32')
        return signal_data, sr

    # Fallback: escribir a archivo temporal y usar scipy.io.wavfile (solo WAV soportado)
    try:
        suffix = '.wav'
        if filename_hint and isinstance(filename_hint, str) and filename_hint.lower().endswith('.mp3'):
            # No podemos leer MP3 con scipy fallback
            raise RuntimeError("pysoundfile no disponible: no se puede leer MP3 sin librerías adicionales. Instala 'soundfile' y libsndfile.")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data_bytes)
            tmp.flush()
            tmp_name = tmp.name

        sr, data = scipy_wavfile.read(tmp_name)
        # Convertir a float32 en rango [-1, 1] si es entero
        if data.dtype.kind in ('i', 'u'):
            # determinar máximo para normalizar según tipo
            max_val = float(np.iinfo(data.dtype).max)
            signal_data = data.astype(np.float32) / max_val
        else:
            signal_data = data.astype(np.float32)
        return signal_data, int(sr)
    except Exception:
        raise


def plot_waveform(time, normalized):
    if HAS_MPL:
        fig_wf, ax_wf = plt.subplots(figsize=(10, 3))
        ax_wf.plot(time, normalized, color="#2b8cbe", linewidth=0.6)
        ax_wf.set_xlabel("Tiempo (s)")
        ax_wf.set_ylabel("Amplitud (normalizada)")
        ax_wf.set_xlim(0, min(time[-1] if len(time) else 0, 10.0))
        ax_wf.grid(alpha=0.3)
        st.pyplot(fig_wf)
        plt.close(fig_wf)
    else:
        # Fallback simple con st.line_chart (no control de ejes)
        try:
            df_wf = pd.DataFrame({"time_s": time, "amplitude": normalized})
            df_wf = df_wf.set_index('time_s')
            st.line_chart(df_wf)
        except Exception:
            st.write("[Vista previa de la forma de onda no disponible — instala matplotlib para gráficos más ricos]")


def plot_spectrum(freqs, mag_display, eps, max_plot_freq):
    mask = freqs <= max_plot_freq
    if HAS_MPL:
        fig_sp, ax_sp = plt.subplots(figsize=(10, 3))
        ax_sp.semilogy(freqs[mask], mag_display[mask] + eps, color="#e34a33")
        ax_sp.set_xlabel("Frecuencia (Hz)")
        ax_sp.set_ylabel("Magnitud (log)")
        ax_sp.grid(alpha=0.3)
        st.pyplot(fig_sp)
        plt.close(fig_sp)
    else:
        try:
            df_sp = pd.DataFrame({"freq": freqs[mask], "mag": mag_display[mask]})
            df_sp = df_sp.set_index('freq')
            st.line_chart(df_sp)
        except Exception:
            st.write("[Vista previa del espectro no disponible — instala matplotlib para gráficos más ricos]")


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
            # Leer bytes y usar soundfile para obtener señal y sample rate (o fallback)
            data_bytes = upload.read()
            signal_data, sr = read_audio(data_bytes, getattr(upload, 'name', None))

            # soundfile devuelve (samples, channels) o (samples,)
            if hasattr(signal_data, 'ndim') and signal_data.ndim > 1:
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
                mag_smoothed = safe_medfilt(mag, kernel_size=5)
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
            plot_waveform(time, normalized)

            st.subheader("Espectro (frequency domain)")
            # limitar eje x a Nyquist
            nyq = sr / 2.0
            # mostrar hasta 5 kHz por defecto o Nyquist si menor
            max_plot_freq = min(5000, nyq)
            plot_spectrum(freqs, mag_display, eps, max_plot_freq)

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

st.markdown("---")
st.write("Sugerencias: puedes ampliar esta app para generar listas de ejercicios, exportar a CSV/PDF, o añadir tipos adicionales (sistemas, factorización, inecuaciones).")
