import tkinter as tk
from tkinter import messagebox
import uuid
import json
import os
from datetime import datetime

CACHE_FILE = "parking_lot.json"

class Vehicle:
    def __init__(self, plate: str, vehicle_type: str = "легковой", speed: int = 60):
        self.id = str(uuid.uuid4())[:8]
        self.plate = plate
        self.vehicle_type = vehicle_type
        self.speed = speed
        self.previous_speed = speed
        self.status = "waiting"
        self.entry_time = None
        self.exit_time = None

    def park(self):
        if self.status == "waiting":
            self.status = "parked"
            self.entry_time = datetime.now()
            return True
        return False

    def leave(self):
        if self.status == "parked":
            self.status = "left"
            self.exit_time = datetime.now()
            return True
        return False
    
    def return_to_waiting(self):
        """Вернуть машину в режим ожидания (из parked или left)"""
        if self.status in ["parked", "left"]:
            self.status = "waiting"
            # Очищаем время заезда и выезда при возврате в ожидание
            if self.status == "waiting":
                self.entry_time = None
                self.exit_time = None
            return True
        return False
    
    def stop(self):
        if self.speed != 0:
            self.previous_speed = self.speed
            self.speed = 0
            return True
        return False
    
    def start(self):
        if self.speed == 0 and self.previous_speed > 0:
            self.speed = self.previous_speed
            return True
        return False

    def to_dict(self):
        return {
            "id": self.id,
            "plate": self.plate,
            "vehicle_type": self.vehicle_type,
            "speed": self.speed,
            "previous_speed": self.previous_speed,
            "status": self.status,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
        }

    @staticmethod
    def from_dict(d):
        v = Vehicle(d["plate"], d["vehicle_type"], d.get("speed", 60))
        v.id = d["id"]
        v.speed = d["speed"]
        v.previous_speed = d.get("previous_speed", d.get("speed", 60))
        v.status = d["status"]
        if d["entry_time"]:
            v.entry_time = datetime.fromisoformat(d["entry_time"])
        if d["exit_time"]:
            v.exit_time = datetime.fromisoformat(d["exit_time"])
        return v

class ParkingLot:
    def __init__(self):
        self.vehicles = []

    def add_vehicle(self, plate: str, vehicle_type: str = "легковой", speed: int = 60):
        car = Vehicle(plate, vehicle_type, speed)
        self.vehicles.append(car)
        return car.id

    def update_speed(self, vehicle_id, new_speed):
        for car in self.vehicles:
            if car.id == vehicle_id:
                if car.speed != 0:
                    car.previous_speed = car.speed
                car.speed = new_speed
                return True
        return False
    
    def stop_vehicle(self, vehicle_id):
        for car in self.vehicles:
            if car.id == vehicle_id:
                return car.stop()
        return False
    
    def start_vehicle(self, vehicle_id):
        for car in self.vehicles:
            if car.id == vehicle_id:
                return car.start()
        return False

    def park_vehicle(self, vehicle_id):
        for car in self.vehicles:
            if car.id == vehicle_id:
                return car.park()
        return None

    def leave_vehicle(self, vehicle_id):
        for car in self.vehicles:
            if car.id == vehicle_id:
                return car.leave()
        return None
    
    def return_to_waiting(self, vehicle_id):
        """Вернуть машину в режим ожидания"""
        for car in self.vehicles:
            if car.id == vehicle_id:
                return car.return_to_waiting()
        return False

    def get_statistics(self):
        total = len(self.vehicles)
        parked = sum(1 for c in self.vehicles if c.status == "parked")
        left = sum(1 for c in self.vehicles if c.status == "left")
        waiting = sum(1 for c in self.vehicles if c.status == "waiting")
        speeds = [c.speed for c in self.vehicles if c.status != "left"]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        return {
            "total": total,
            "parked": parked,
            "left": left,
            "waiting": waiting,
            "avg_speed": avg_speed,
        }

    def get_vehicle_list(self):
        lines = []
        for car in self.vehicles:
            status_text = {
                "waiting": "ожидает",
                "parked": "на стоянке",
                "left": "уехала",
            }.get(car.status, car.status)
            entry_str = car.entry_time.strftime("%H:%M:%S") if car.entry_time else "---"
            exit_str = car.exit_time.strftime("%H:%M:%S") if car.exit_time else "---"
            speed_display = f"{car.speed} км/ч"
            if car.speed == 0 and car.previous_speed > 0:
                speed_display += " (стоит)"
            lines.append(f"{car.id} | {car.plate} ({car.vehicle_type}) | {speed_display:>12} | {status_text} | заезд: {entry_str} | выезд: {exit_str}")
        return lines

    def get_vehicle_by_index(self, index):
        if 0 <= index < len(self.vehicles):
            return self.vehicles[index]
        return None

    def to_dict_list(self):
        return [car.to_dict() for car in self.vehicles]

    @staticmethod
    def from_dict_list(data):
        parking = ParkingLot()
        for d in data:
            car = Vehicle.from_dict(d)
            parking.vehicles.append(car)
        return parking

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Автостоянка – полное управление (с возвратом в ожидание)")
        self.parking = ParkingLot()
        self.load_cache()

        # --- Верхняя панель: добавление машины ---
        frame_add = tk.LabelFrame(root, text="Добавление нового автомобиля", padx=5, pady=5)
        frame_add.pack(pady=5, fill=tk.X, padx=10)

        tk.Label(frame_add, text="Госномер:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.E)
        self.plate_entry = tk.Entry(frame_add, width=12)
        self.plate_entry.grid(row=0, column=1, padx=5, pady=2)
        self.plate_entry.insert(0, "А123БВ")

        tk.Label(frame_add, text="Тип:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.E)
        self.type_entry = tk.Entry(frame_add, width=10)
        self.type_entry.grid(row=0, column=3, padx=5, pady=2)
        self.type_entry.insert(0, "легковой")

        tk.Label(frame_add, text="Скорость (км/ч):").grid(row=0, column=4, padx=5, pady=2, sticky=tk.E)
        self.speed_entry = tk.Entry(frame_add, width=8)
        self.speed_entry.grid(row=0, column=5, padx=5, pady=2)
        self.speed_entry.insert(0, "60")

        tk.Button(frame_add, text="➕ Добавить машину", command=self.add_vehicle, bg="#90EE90").grid(row=0, column=6, padx=10, pady=2)

        # --- Панель: редактирование скорости ---
        frame_edit = tk.LabelFrame(root, text="Редактирование скорости", padx=5, pady=5)
        frame_edit.pack(pady=5, fill=tk.X, padx=10)

        tk.Label(frame_edit, text="Новая скорость (км/ч):").pack(side=tk.LEFT, padx=5)
        self.new_speed_entry = tk.Entry(frame_edit, width=8)
        self.new_speed_entry.pack(side=tk.LEFT, padx=5)
        self.new_speed_entry.insert(0, "60")
        tk.Button(frame_edit, text="✏️ Обновить скорость", command=self.update_speed, bg="#FFD700").pack(side=tk.LEFT, padx=5)

        # --- Панель: Стоп/Старт ---
        frame_stop_start = tk.LabelFrame(root, text="Управление движением", padx=5, pady=5)
        frame_stop_start.pack(pady=5, fill=tk.X, padx=10)
        
        self.stop_btn = tk.Button(frame_stop_start, text="🛑 СТОП (Сбросить скорость до 0)", command=self.stop_vehicle,
                                  bg="#FF4444", fg="white", font=("Arial", 10, "bold"), width=22, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_btn = tk.Button(frame_stop_start, text="▶️ СТАРТ (Восстановить скорость)", command=self.start_vehicle,
                                   bg="#44FF44", fg="black", font=("Arial", 10, "bold"), width=22, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame_stop_start, text="Стоп: 0 км/ч | Старт: вернуть скорость", 
                 font=("Arial", 8), fg="gray").pack(side=tk.LEFT, padx=10)

        # --- Список машин ---
        frame_list = tk.LabelFrame(root, text="Список автомобилей", padx=5, pady=5)
        frame_list.pack(pady=5, fill=tk.BOTH, expand=True, padx=10)

        scrollbar = tk.Scrollbar(frame_list)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame_list, height=12, width=105, yscrollcommand=scrollbar.set, font=("Courier", 9))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        # --- Панель управления стоянкой ---
        frame_control = tk.LabelFrame(root, text="Управление стоянкой", padx=5, pady=5)
        frame_control.pack(pady=5, fill=tk.X, padx=10)

        # Статус выбранной машины
        self.selected_info = tk.Label(frame_control, text="❌ Машина не выбрана", font=("Arial", 10, "bold"), fg="red")
        self.selected_info.pack(side=tk.LEFT, padx=10)

        # Кнопки управления
        btn_frame = tk.Frame(frame_control)
        btn_frame.pack(side=tk.RIGHT)

        self.park_btn = tk.Button(btn_frame, text="🚗 ЗАЕХАТЬ", command=self.park_vehicle, 
                                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=12, state=tk.DISABLED)
        self.park_btn.pack(side=tk.LEFT, padx=5)

        self.leave_btn = tk.Button(btn_frame, text="🚙 ВЫЕХАТЬ", command=self.leave_vehicle, 
                                   bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=12, state=tk.DISABLED)
        self.leave_btn.pack(side=tk.LEFT, padx=5)
        
        # Новая кнопка "Вернуть в ожидание"
        self.waiting_btn = tk.Button(btn_frame, text="🔄 В ОЖИДАНИЕ", command=self.return_to_waiting, 
                                     bg="#FF9800", fg="white", font=("Arial", 10, "bold"), width=14, state=tk.DISABLED)
        self.waiting_btn.pack(side=tk.LEFT, padx=5)

        # --- Нижняя панель ---
        frame_bottom = tk.Frame(root)
        frame_bottom.pack(pady=5, fill=tk.X, padx=10)

        tk.Button(frame_bottom, text="📊 Статистика", command=self.show_statistics, width=15, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_bottom, text="💾 Сохранить в файл", command=self.save_to_file, width=15, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_bottom, text="🔄 Обновить список", command=self.refresh_list, width=15, bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(frame_bottom, text="✅ Готов", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

        self.selected_index = None
        self.refresh_list()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.parking = ParkingLot.from_dict_list(data)
                print(f"Загружено {len(self.parking.vehicles)} машин")
            except Exception as e:
                messagebox.showwarning("Кэш", f"Ошибка загрузки: {e}")

    def save_to_file(self):
        data = self.parking.to_dict_list()
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Сохранено", f"Данные сохранены в {CACHE_FILE}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

    def on_closing(self):
        self.save_to_file()
        self.root.destroy()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for item in self.parking.get_vehicle_list():
            self.listbox.insert(tk.END, item)
        self.selected_index = None
        self.selected_info.config(text="❌ Машина не выбрана", fg="red")
        self.park_btn.config(state=tk.DISABLED)
        self.leave_btn.config(state=tk.DISABLED)
        self.waiting_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self.status_label.config(text=f"✅ Всего машин: {len(self.parking.vehicles)}")

    def on_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.selected_index = selection[0]
            car = self.parking.get_vehicle_by_index(self.selected_index)
            if car:
                status_emoji = "🟢" if car.status == "parked" else "🟡" if car.status == "waiting" else "⚪"
                speed_info = f"{car.speed} км/ч"
                if car.speed == 0 and car.previous_speed > 0:
                    speed_info += f" (было {car.previous_speed} км/ч)"
                self.selected_info.config(text=f"{status_emoji} Выбрана: {car.plate} ({car.vehicle_type}) | {speed_info} | {car.status}", fg="blue")
                
                # Активируем/деактивируем кнопки в зависимости от статуса
                if car.status == "waiting":
                    self.park_btn.config(state=tk.NORMAL, bg="#4CAF50")
                    self.leave_btn.config(state=tk.DISABLED, bg="#f44336")
                    self.waiting_btn.config(state=tk.DISABLED, bg="#FF9800")  # уже в ожидании
                elif car.status == "parked":
                    self.park_btn.config(state=tk.DISABLED, bg="#4CAF50")
                    self.leave_btn.config(state=tk.NORMAL, bg="#f44336")
                    self.waiting_btn.config(state=tk.NORMAL, bg="#FF9800")  # можно вернуть в ожидание
                else:  # left
                    self.park_btn.config(state=tk.DISABLED, bg="#4CAF50")
                    self.leave_btn.config(state=tk.DISABLED, bg="#f44336")
                    self.waiting_btn.config(state=tk.NORMAL, bg="#FF9800")  # можно вернуть уехавшую машину
                
                # Управление кнопками Стоп/Старт
                if car.status in ["waiting", "parked"]:
                    if car.speed > 0:
                        self.stop_btn.config(state=tk.NORMAL, bg="#FF4444")
                        self.start_btn.config(state=tk.DISABLED, bg="#44FF44")
                    elif car.speed == 0 and car.previous_speed > 0:
                        self.stop_btn.config(state=tk.DISABLED, bg="#FF4444")
                        self.start_btn.config(state=tk.NORMAL, bg="#44FF44")
                    else:
                        self.stop_btn.config(state=tk.DISABLED, bg="#FF4444")
                        self.start_btn.config(state=tk.DISABLED, bg="#44FF44")
                else:
                    self.stop_btn.config(state=tk.DISABLED, bg="#FF4444")
                    self.start_btn.config(state=tk.DISABLED, bg="#44FF44")
                
                self.new_speed_entry.delete(0, tk.END)
                self.new_speed_entry.insert(0, str(car.speed))

    def add_vehicle(self):
        plate = self.plate_entry.get().strip()
        vtype = self.type_entry.get().strip()
        try:
            speed = int(self.speed_entry.get().strip())
            if speed < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Ошибка", "Скорость должна быть >= 0")
            return
        if not plate:
            messagebox.showwarning("Ошибка", "Введите госномер")
            return
        if not vtype:
            vtype = "легковой"
        new_id = self.parking.add_vehicle(plate, vtype, speed)
        messagebox.showinfo("Добавлено", f"Машина {plate} добавлена. ID: {new_id}")
        self.refresh_list()

    def update_speed(self):
        if self.selected_index is None:
            messagebox.showwarning("Ошибка", "Выберите машину")
            return
        car = self.parking.get_vehicle_by_index(self.selected_index)
        if not car:
            return
        try:
            new_speed = int(self.new_speed_entry.get().strip())
            if new_speed < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Ошибка", "Скорость должна быть >= 0")
            return
        if self.parking.update_speed(car.id, new_speed):
            action = "остановлена" if new_speed == 0 else f"установлена скорость {new_speed} км/ч"
            self.status_label.config(text=f"✅ Скорость обновлена: {car.plate} {action}")
            self.refresh_list()
            self.on_select(None)

    def stop_vehicle(self):
        if self.selected_index is None:
            messagebox.showwarning("Ошибка", "Выберите машину")
            return
        car = self.parking.get_vehicle_by_index(self.selected_index)
        if not car:
            return
        
        if car.speed == 0:
            self.status_label.config(text=f"⚠️ Машина {car.plate} уже стоит на месте")
            return
        
        if self.parking.stop_vehicle(car.id):
            self.status_label.config(text=f"🛑 Машина {car.plate} остановлена (скорость 0 км/ч)")
            self.refresh_list()
            self.on_select(None)
        else:
            messagebox.showerror("Ошибка", "Не удалось остановить машину")

    def start_vehicle(self):
        if self.selected_index is None:
            messagebox.showwarning("Ошибка", "Выберите машину")
            return
        car = self.parking.get_vehicle_by_index(self.selected_index)
        if not car:
            return
        
        if car.speed > 0:
            self.status_label.config(text=f"⚠️ Машина {car.plate} уже движется")
            return
        
        if car.previous_speed == 0:
            messagebox.showwarning("Предупреждение", f"У машины {car.plate} нет сохранённой скорости")
            return
        
        if self.parking.start_vehicle(car.id):
            self.status_label.config(text=f"▶️ Машина {car.plate} запущена (скорость {car.speed} км/ч)")
            self.refresh_list()
            self.on_select(None)
        else:
            messagebox.showerror("Ошибка", "Не удалось запустить машину")

    def park_vehicle(self):
        if self.selected_index is None:
            messagebox.showwarning("Ошибка", "Выберите машину")
            return
        car = self.parking.get_vehicle_by_index(self.selected_index)
        if not car:
            return
        
        result = self.parking.park_vehicle(car.id)
        if result:
            self.status_label.config(text=f"✅ {car.plate} заехала на стоянку в {datetime.now().strftime('%H:%M:%S')}")
            self.refresh_list()
        else:
            messagebox.showwarning("Ошибка", f"Нельзя заехать. Статус: {car.status}")

    def leave_vehicle(self):
        if self.selected_index is None:
            messagebox.showwarning("Ошибка", "Выберите машину")
            return
        car = self.parking.get_vehicle_by_index(self.selected_index)
        if not car:
            return
        
        result = self.parking.leave_vehicle(car.id)
        if result:
            speed_text = f"{car.speed} км/ч" if car.speed > 0 else "0 км/ч (выезд на эвакуаторе)"
            self.status_label.config(text=f"🚙 {car.plate} выехала со скоростью {speed_text} в {datetime.now().strftime('%H:%M:%S')}")
            self.refresh_list()
        else:
            messagebox.showwarning("Ошибка", f"Нельзя выехать. Статус: {car.status}")

    def return_to_waiting(self):
        """Вернуть машину в режим ожидания"""
        if self.selected_index is None:
            messagebox.showwarning("Ошибка", "Выберите машину")
            return
        car = self.parking.get_vehicle_by_index(self.selected_index)
        if not car:
            return
        
        if car.status == "waiting":
            self.status_label.config(text=f"⚠️ Машина {car.plate} уже в режиме ожидания")
            return
        
        result = self.parking.return_to_waiting(car.id)
        if result:
            self.status_label.config(text=f"🔄 Машина {car.plate} возвращена в режим ожидания (была: {car.status})")
            self.refresh_list()
        else:
            messagebox.showerror("Ошибка", "Не удалось вернуть машину в режим ожидания")

    def show_statistics(self):
        stats = self.parking.get_statistics()
        left_speeds = [c.speed for c in self.parking.vehicles if c.status == "left"]
        avg_left_speed = sum(left_speeds) / len(left_speeds) if left_speeds else 0
        zero_speed_count = sum(1 for c in self.parking.vehicles if c.speed == 0 and c.status != "left")
        stopped_count = sum(1 for c in self.parking.vehicles if c.speed == 0 and c.previous_speed > 0 and c.status != "left")
        
        text = (
            f"╔══════════════════════════════════════╗\n"
            f"║        СТАТИСТИКА ПАРКОВКИ          ║\n"
            f"╠══════════════════════════════════════╣\n"
            f"║ Всего машин в системе: {stats['total']:>3}                    ║\n"
            f"║ На стоянке сейчас:   {stats['parked']:>3}                    ║\n"
            f"║ Уехали:              {stats['left']:>3}                    ║\n"
            f"║ Ожидают заезда:      {stats['waiting']:>3}                    ║\n"
            f"╠══════════════════════════════════════╣\n"
            f"║ Средняя скорость:    {stats['avg_speed']:>5.1f} км/ч            ║\n"
            f"║ Средняя уехавших:    {avg_left_speed:>5.1f} км/ч            ║\n"
            f"║ С нулевой скоростью: {zero_speed_count:>3}                     ║\n"
            f"║ Остановленных:       {stopped_count:>3}                     ║\n"
            f"╚══════════════════════════════════════╝"
        )
        messagebox.showinfo("📊 Статистика", text)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1150x650")
    app = App(root)
    root.mainloop()