import pyaudio
import numpy as np
import os
import time
from gtts import gTTS
from audioplayer import AudioPlayer
from pynput.keyboard import Controller, Key

# --- PENGATURAN DASAR ---
CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # Diperbaiki dari 34100 ke nilai standar
DEVICE_INDEX = 1
COOLDOWN = 2.0  # Waktu cooldown antar deteksi (detik)
FAKTOR_SENSITIVITAS = 1.2
UPDATE_INTERVAL = 2.0

# Fungsi untuk mengucapkan kalimat
def ucapkan_kalimat(teks):
    try:
        print(f"Program berkata: '{teks}'")
        tts = gTTS(text=teks, lang='id', slow=False)
        nama_file_suara = "respons_suara.mp3"
        tts.save(nama_file_suara)
        AudioPlayer(nama_file_suara).play(block=True)
        os.remove(nama_file_suara)
    except Exception as e:
        print(f"[Peringatan] Tidak bisa memutar suara: {e}")

# Fungsi untuk menekan tombol Print
def tekan_tombol_print():
    try:
        print("Mensimulasikan Ctrl+P ... Enter")
        time.sleep(3.5)
        keyboard = Controller()
        keyboard.press(Key.ctrl)
        keyboard.press('p')
        keyboard.release('p')
        keyboard.release(Key.ctrl)
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)
    except Exception as e:
        print(f"[Peringatan] Tidak bisa menekan tombol: {e}")

# Kalibrasi mikrofon
def kalibrasi_mikrofon(stream):
    print("Kalibrasi sedang berlangsung...")
    start = time.time()
    rms_vals = []

    while time.time() - start < 2:  # Diperpanjang ke 2 detik untuk akurasi lebih baik
        data = stream.read(CHUNK, exception_on_overflow=False)
        np_data = np.frombuffer(data, dtype=np.int16)
        if np.any(np.isfinite(np_data)):
            mean_val = np.mean(np_data.astype(np.float64) ** 2)
            rms_val = np.sqrt(mean_val) if mean_val > 0 else 0
            rms_vals.append(rms_val)

    if rms_vals:
        noise = np.mean(rms_vals)
        threshold = max(noise * FAKTOR_SENSITIVITAS, 100)
    else:
        noise = 0
        threshold = 100

    print(f"Kalibrasi selesai: kebisingan={noise:.2f}, ambang awal={threshold:.2f}")
    return threshold, noise

# Fungsi utama
def listen_and_print():
    p = pyaudio.PyAudio()
    stream = None
    try:
        try:
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                            input=True, frames_per_buffer=CHUNK, input_device_index=DEVICE_INDEX)
        except Exception as e:
            print(f"[Peringatan] Device index {DEVICE_INDEX} gagal, menggunakan default: {e}")
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                            input=True, frames_per_buffer=CHUNK)

        threshold, noise = kalibrasi_mikrofon(stream)
        print("Program siap! Dengarkan tepukan tangan (1x print)...")

        printed = False
        last_clap_time = 0
        last_update_time = time.time()
        rms_history = []

        while not printed:
            data = stream.read(CHUNK, exception_on_overflow=False)
            np_data = np.frombuffer(data, dtype=np.int16)
            mean_val = np.mean(np_data.astype(np.float64) ** 2)
            rms_val = np.sqrt(mean_val) if mean_val > 0 else 0
            rms_history.append(rms_val)

            if len(rms_history) > 100:
                rms_history.pop(0)

            # Update threshold secara periodik
            if time.time() - last_update_time >= UPDATE_INTERVAL:
                noise = np.mean(rms_history) if rms_history else 0
                threshold = max(noise * FAKTOR_SENSITIVITAS, 100)
                last_update_time = time.time()

            # Deteksi tepukan: Jika RMS > threshold dan cooldown terpenuhi
            if rms_val > threshold and (time.time() - last_clap_time) > COOLDOWN:
                print(f"Tepukan terdeteksi! RMS: {rms_val:.2f} > Threshold: {threshold:.2f}")
                last_clap_time = time.time()
                tekan_tombol_print()
                ucapkan_kalimat("Tepukan tangan terdeteksi, mencetak dokumen.")
                printed = True  # Hentikan loop setelah satu deteksi

    except Exception as e:
        print(f"[Error] Terjadi kesalahan: {e}")
    finally:
        # Cleanup
        if stream:
            stream.stop_stream()
            stream.close()
        p.terminate()
        print("Program selesai.")

# Jalankan program
if __name__ == "__main__":
    listen_and_print()
