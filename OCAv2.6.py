import tkinter as tk
from tkinter import messagebox
import json
import threading
import time
import datetime
import shelve
import os
import sys

# ── Paket kontrolleri ────────────────────────────────────────────────────────
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    print(f"[HATA] Eksik paket: {e}")
    print("Lütfen calistirin: pip install selenium webdriver-manager pyautogui pillow")
    sys.exit(1)

try:
    import pyautogui
except ImportError:
    print("[HATA] pyautogui bulunamadı. Çalıştırın: pip install pyautogui pillow")
    sys.exit(1)

# ── Sabitler ─────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_FILE = os.path.join(BASE_DIR, "schedule.json")
USER_FILE     = os.path.join(BASE_DIR, "user_info")

# ── Durum değişkenleri ───────────────────────────────────────────────────────
lesson_mapping   = []   # [(day, index), ...]
joined_lessons   = set()  # Aynı derse iki kez girmeyi engeller
current_username = ""
current_password = ""


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def resource_path(filename: str) -> str:
    """IDE'den veya PyInstaller .exe'sinden çalışırken doğru yolu döndürür."""
    if getattr(sys, "frozen", False):   # PyInstaller paketi
        base = sys._MEIPASS
    else:                               # Normal Python / IDE
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


def check_images():
    """Gerekli görüntü dosyalarının varlığını kontrol eder."""
    missing = []
    for img in ["open.png", "zoom_join.png"]:
        path = resource_path(img)
        if not os.path.exists(path):
            missing.append(path)
    if missing:
        print("[UYARI] Şu görüntü dosyaları bulunamadı:")
        for m in missing:
            print(f"  - {m}")
        print("  pyautogui görsel eşleme çalışmayacak; klavye yedeği devreye girecek.")


# ── Kimlik bilgileri ──────────────────────────────────────────────────────────

def save_credentials():
    global current_username, current_password
    current_username = username_entry.get().strip()
    current_password = password_entry.get().strip()
    if not current_username or not current_password:
        messagebox.showwarning("Uyarı", "Kullanıcı adı ve şifre boş olamaz!")
        return
    with shelve.open(USER_FILE) as db:
        db["username"] = current_username
        db["password"] = current_password
    messagebox.showinfo("Bilgi", "Kullanıcı bilgileri kaydedildi!")


def load_credentials():
    global current_username, current_password
    try:
        with shelve.open(USER_FILE) as db:
            current_username = db.get("username", "")
            current_password = db.get("password", "")
            username_entry.insert(0, current_username)
            password_entry.insert(0, current_password)
    except Exception:
        pass


# ── Ders listesi ──────────────────────────────────────────────────────────────

def load_schedule() -> dict:
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_schedule(schedule: dict):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)


def update_lesson_list():
    global lesson_mapping
    lesson_listbox.delete(0, tk.END)
    lesson_mapping = []
    schedule = load_schedule()
    for day, lessons in schedule.items():
        for idx, lesson in enumerate(lessons):
            display_text = f"{day}: {lesson['hour']} - {lesson.get('desc', '')}"
            lesson_listbox.insert(tk.END, display_text)
            lesson_mapping.append((day, idx))


def add_lesson():
    day  = day_var.get()
    hour = hour_entry.get().strip()
    desc = desc_entry.get().strip()

    if not hour:
        messagebox.showwarning("Uyarı", "Ders saatini giriniz!")
        return

    # Basit saat formatı doğrulaması
    try:
        datetime.datetime.strptime(hour, "%H:%M")
    except ValueError:
        messagebox.showwarning("Uyarı", "Saat formatı HH:MM olmalıdır! (örn: 09:30)")
        return

    schedule = load_schedule()
    schedule.setdefault(day, []).append({"hour": hour, "desc": desc})
    save_schedule(schedule)
    messagebox.showinfo("Bilgi", f"Ders eklendi: {day} günü saat {hour}")
    update_lesson_list()


def delete_lesson():
    selected = lesson_listbox.curselection()
    if not selected:
        messagebox.showwarning("Uyarı", "Silinecek dersi seçiniz!")
        return

    day, lesson_index = lesson_mapping[selected[0]]
    schedule = load_schedule()

    if day in schedule and lesson_index < len(schedule[day]):
        del schedule[day][lesson_index]
        if not schedule[day]:
            del schedule[day]
        save_schedule(schedule)
        messagebox.showinfo("Bilgi", "Ders silindi!")
        update_lesson_list()
    else:
        messagebox.showerror("Hata", "Ders bulunamadı!")


# ── Zamanlayıcı ───────────────────────────────────────────────────────────────

def check_schedule():
    """Arka planda sürekli çalışarak ders saatlerini kontrol eder."""
    while True:
        try:
            now          = datetime.datetime.now()
            current_day  = now.strftime("%A")
            schedule     = load_schedule()

            if current_day in schedule:
                for lesson in schedule[current_day]:
                    lesson_key = f"{current_day}-{lesson['hour']}"

                    # Aynı derse aynı gün tekrar girme
                    if lesson_key in joined_lessons:
                        continue

                    # 30 saniyelik toleranslı zaman karşılaştırması
                    lesson_time = datetime.datetime.strptime(lesson["hour"], "%H:%M").replace(
                        year=now.year, month=now.month, day=now.day
                    )
                    diff = abs((now - lesson_time).total_seconds())

                    if diff <= 30:
                        print(f"[BİLGİ] Ders başlıyor: {lesson_key}")
                        joined_lessons.add(lesson_key)
                        threading.Thread(target=run_selenium, daemon=True).start()
                        break

        except Exception as e:
            print(f"[HATA] check_schedule: {e}")

        time.sleep(20)


# ── Selenium otomasyonu ───────────────────────────────────────────────────────

def run_selenium():
    """Okul portalına giriş yaparak derse katılır."""
    username = current_username
    password = current_password

    if not username or not password:
        messagebox.showwarning("Uyarı", "Lütfen önce kullanıcı bilgilerini girin ve kaydedin!")
        return

    print("[BİLGİ] Chrome başlatılıyor...")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

    try:
        # ── Giriş ──
        driver.get("https://online.yildiz.edu.tr/Account/Login")
        driver.find_element(By.ID, "Username").send_keys(username)
        driver.find_element(By.ID, "Password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@onclick='LMS.CORE.Account.Login.start();']").click()

        wait = WebDriverWait(driver, 15)

        # ── Etkinlik Akışı ──
        flow_tab = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(text(),'ETKİNLİK AKIŞI')]")
        ))
        flow_tab.click()

        # ── Mavi butona tıkla ──
        try:
            buttons = wait.until(EC.presence_of_all_elements_located(
                (By.CLASS_NAME, "timeline-content")
            ))
            for btn in buttons:
                if btn.value_of_css_property("background-color") == "rgba(0, 81, 146, 1)":
                    btn.click()
                    print("[BİLGİ] Mavi butona tıklandı.")
                    break
        except Exception as e:
            print(f"[UYARI] Mavi buton bulunamadı: {e}")

        # ── Derse Katıl ──
        join_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(text(),'Derse Katıl')]")
        ))
        join_button.click()
        print("[BİLGİ] 'Derse Katıl' butonuna tıklandı.")

        time.sleep(5)

        # ── open.png: Aç / Başlat diyalogu ──
        open_img = resource_path("open.png")
        if os.path.exists(open_img):
            location = pyautogui.locateOnScreen(open_img, confidence=0.8, grayscale=True)
            if location:
                pyautogui.click(location)
                print("[BİLGİ] open.png bulundu ve tıklandı.")
            else:
                print("[UYARI] open.png ekranda bulunamadı; klavye yedеği kullanılıyor.")
                pyautogui.press("left")
                time.sleep(0.3)
                pyautogui.press("enter")
        else:
            print("[UYARI] open.png dosyası yok; klavye yedеği kullanılıyor.")
            pyautogui.press("left")
            time.sleep(0.3)
            pyautogui.press("enter")

        time.sleep(2)

    except Exception as e:
        print(f"[HATA] Selenium adımında sorun: {e}")
    finally:
        driver.quit()
        print("[BİLGİ] Tarayıcı kapatıldı.")

    # ── zoom_join.png: Zoom katıl butonu ──
    time.sleep(3)
    zoom_img = resource_path("zoom_join.png")
    if os.path.exists(zoom_img):
        location = pyautogui.locateCenterOnScreen(zoom_img, confidence=0.8, grayscale=True)
        if location:
            pyautogui.click(location)
            print("[BİLGİ] Zoom 'Katıl' butonuna tıklandı.")
        else:
            print("[UYARI] zoom_join.png ekranda bulunamadı.")
    else:
        print("[UYARI] zoom_join.png dosyası yok.")

    time.sleep(10)
    print("[BİLGİ] Otomasyon tamamlandı.")


# ── Arayüz ───────────────────────────────────────────────────────────────────

root = tk.Tk()
root.title("Online Ders Otomasyonu")
root.resizable(False, False)

# Kullanıcı bilgileri
tk.Label(root, text="Okul Maili:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
username_entry = tk.Entry(root, width=25)
username_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(root, text="Şifre:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
password_entry = tk.Entry(root, show="*", width=25)
password_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Button(root, text="Bilgileri Kaydet", command=save_credentials, width=20).grid(
    row=2, column=0, columnspan=2, pady=5
)

tk.Frame(root, height=1, bg="gray").grid(row=3, column=0, columnspan=2, sticky="ew", padx=5)

# Ders ekleme
tk.Label(root, text="Gün:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
day_var = tk.StringVar(root, value="Monday")
tk.OptionMenu(root, day_var,
              "Monday", "Tuesday", "Wednesday", "Thursday",
              "Friday", "Saturday", "Sunday").grid(row=4, column=1, padx=5, pady=5, sticky="w")

tk.Label(root, text="Saat (HH:MM):").grid(row=5, column=0, padx=5, pady=5, sticky="e")
hour_entry = tk.Entry(root, width=10)
hour_entry.grid(row=5, column=1, padx=5, pady=5, sticky="w")

tk.Label(root, text="Ders Adı:").grid(row=6, column=0, padx=5, pady=5, sticky="e")
desc_entry = tk.Entry(root, width=25)
desc_entry.grid(row=6, column=1, padx=5, pady=5)

tk.Button(root, text="Ders Ekle", command=add_lesson, width=20).grid(
    row=7, column=0, columnspan=2, pady=5
)

tk.Frame(root, height=1, bg="gray").grid(row=8, column=0, columnspan=2, sticky="ew", padx=5)

# Manuel giriş & silme
tk.Button(root, text="Şimdi Derse Gir", command=lambda: threading.Thread(target=run_selenium, daemon=True).start(),
          width=20, bg="#0051A2", fg="white").grid(row=9, column=0, columnspan=2, pady=5)

tk.Button(root, text="Seçili Dersi Sil", command=delete_lesson, width=20).grid(
    row=10, column=0, columnspan=2, pady=3
)

# Ders listesi
tk.Label(root, text="Kayıtlı Dersler:").grid(row=11, column=0, columnspan=2, pady=(10, 0))
lesson_listbox = tk.Listbox(root, width=40, height=10)
lesson_listbox.grid(row=12, column=0, columnspan=2, padx=5, pady=5)

# ── Başlangıç ────────────────────────────────────────────────────────────────
check_images()
load_credentials()
update_lesson_list()

threading.Thread(target=check_schedule, daemon=True).start()
print("[BİLGİ] Zamanlayıcı başlatıldı. Ders saatleri takip ediliyor...")

root.mainloop()
