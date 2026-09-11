"""
Умный сканер системы. Сам находит все расшаренные папки и сетевые ресурсы.
"""
import os
import json
import subprocess
import winreg
from pathlib import Path
from datetime import datetime
from config import PROJECT_ROOT, INDEX_EXTENSIONS

INDEX_FILE = PROJECT_ROOT / "data" / "system_index.json"


def run_command(cmd):
    """Выполняет системную команду и возвращает вывод"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout
    except:
        return ""


def find_local_shares():
    """Находит все расшаренные папки на этом компьютере"""
    print(" Поиск локальных расшаренных папок...")
    shares = []
    
    # Способ 1: через команду net share
    output = run_command("net share")
    for line in output.split("\n"):
        line = line.strip()
        if line and "----" not in line and "Share name" not in line and "The command" not in line:
            parts = line.split(None, 1)
            if len(parts) >= 2:
                share_name = parts[0]
                share_path = parts[1].split()[0] if parts[1] else ""
                # Исключаем системные шары
                if share_name.lower() not in ["admin$", "c$", "ipc$", "print$"]:
                    if Path(share_path).exists():
                        shares.append({
                            "name": share_name,
                            "path": share_path,
                            "type": "local_share"
                        })
    
    print(f"   Найдено {len(shares)} локальных шар")
    return shares


def find_network_drives():
    """Находит подключенные сетевые диски"""
    print("🔍 Поиск подключенных сетевых дисков...")
    drives = []
    
    output = run_command("net use")
    for line in output.split("\n"):
        line = line.strip()
        # Ищем строки с буквами дисков (X:, Y:, Z: и т.д.)
        if len(line) > 3 and line[1] == ':' and line[2] == ' ':
            parts = line.split(None, 2)
            if len(parts) >= 3:
                drive_letter = parts[0]
                remote_path = parts[2]
                if remote_path.startswith("\\\\") and "OK" in line:
                    drives.append({
                        "name": drive_letter,
                        "path": remote_path,
                        "type": "network_drive"
                    })
    
    print(f"   Найдено {len(drives)} сетевых дисков")
    return drives


def find_network_computers():
    """Пытается найти компьютеры в локальной сети"""
    print("🔍 Поиск компьютеров в сети...")
    computers = []
    
    # Способ 1: через net view
    output = run_command("net view")
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("\\\\"):
            computer_name = line.split()[0].replace("\\\\", "")
            computers.append(computer_name)
    
    # Способ 2: сканируем стандартный диапазон 192.168.1.x (быстрый пинг)
    # Можно отключить, если сеть большая
    local_subnet = "192.168.89."  # Измени под свою подсеть
    print(f"   Сканирование подсети {local_subnet}x...")
    
    for i in range(1, 20):  # Проверяем только первые 20 адресов для скорости
        ip = f"{local_subnet}{i}"
        result = run_command(f"ping -n 1 -w 500 {ip}")
        if "TTL=" in result:
            # Пытаемся получить имя компьютера
            name_output = run_command(f"nbtstat -A {ip}")
            name = ip
            for nline in name_output.split("\n"):
                if "<00>" in nline and "UNIQUE" in nline:
                    name = nline.split("<00>")[0].strip()
                    break
            computers.append(name)
    
    # Убираем дубликаты
    computers = list(set(computers))
    print(f"   Найдено {len(computers)} компьютеров")
    return computers


def scan_folder(folder_path, max_files=500, max_depth=5):
    """Сканирует папку и возвращает список файлов с метаданными"""
    docs = []
    base = Path(folder_path)
    
    if not base.exists():
        return docs
    
    try:
        for file in base.rglob("*"):
            # Проверяем глубину
            try:
                depth = len(file.relative_to(base).parts)
                if depth > max_depth:
                    continue
            except:
                continue
            
            if file.is_file() and file.suffix.lower() in INDEX_EXTENSIONS:
                try:
                    rel_path = file.relative_to(base)
                    folder = str(rel_path.parent) if rel_path.parent != Path('.') else "Корень"
                    
                    docs.append({
                        "name": file.name,
                        "full_path": str(file),
                        "folder": folder,
                        "extension": file.suffix.lower(),
                        "size_mb": round(file.stat().st_size / (1024*1024), 2),
                        "modified": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d")
                    })
                    
                    if len(docs) >= max_files:
                        break
                except:
                    pass
    except PermissionError:
        pass
    
    return docs


def scan_all_network_resources(computers):
    """Сканирует все найденные сетевые ресурсы"""
    print("\n🔍 Сканирование сетевых ресурсов...")
    all_docs = []
    
    # 1. Сканируем локальные шары
    shares = find_local_shares()
    for share in shares:
        print(f"   📂 Сканирую шару: {share['name']} ({share['path']})")
        docs = scan_folder(share["path"], max_files=200)
        for doc in docs:
            doc["source"] = f"Локальная шара: {share['name']}"
        all_docs.extend(docs)
    
    # 2. Сканируем сетевые диски
    drives = find_network_drives()
    for drive in drives:
        print(f"    Сканирую сетевой диск: {drive['name']} ({drive['path']})")
        docs = scan_folder(drive["path"], max_files=300)
        for doc in docs:
            doc["source"] = f"Сетевой диск: {drive['name']}"
        all_docs.extend(docs)
    
    # 3. Сканируем стандартные шары на найденных компьютерах
    for computer in computers:
        print(f"   📂 Проверяю компьютер: {computer}")
        # Пытаемся найти общие папки
        output = run_command(f"net view \\\\{computer}")
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("\\\\") and "Disk" in line:
                share_path = line.split()[0]
                print(f"      → Нашел шару: {share_path}")
                docs = scan_folder(share_path, max_files=100)
                for doc in docs:
                    doc["source"] = f"Компьютер: {computer}"
                all_docs.extend(docs)
    
    print(f"\n✅ Всего найдено {len(all_docs)} документов в сети")
    return all_docs


def scan_registry_programs():
    """Сканирует реестр для получения списка программ"""
    print("🔍 Сканирование установленных программ...")
    programs = []
    
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    
    for hive, path in registry_paths:
        try:
            key = winreg.OpenKey(hive, path)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    
                    try:
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                        version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                        
                        exe_path = None
                        if location and Path(location).exists():
                            for exe in Path(location).glob("*.exe"):
                                if "uninstall" not in exe.name.lower():
                                    exe_path = str(exe)
                                    break
                        
                        if name:
                            programs.append({
                                "name": name,
                                "exe": exe_path or location,
                                "version": version,
                                "category": "installed"
                            })
                    except:
                        pass
                    
                    winreg.CloseKey(subkey)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except:
            pass
    
    # Системные приложения
    system_apps = [
        {"name": "outlook", "exe": "outlook", "category": "office"},
        {"name": "word", "exe": "winword", "category": "office"},
        {"name": "excel", "exe": "excel", "category": "office"},
        {"name": "powerpoint", "exe": "powerpnt", "category": "office"},
        {"name": "браузер edge", "exe": "msedge", "category": "browser"},
        {"name": "chrome", "exe": "chrome", "category": "browser"},
        {"name": "калькулятор", "exe": "calc", "category": "utilities"},
        {"name": "блокнот", "exe": "notepad", "category": "utilities"},
        {"name": "paint", "exe": "mspaint", "category": "utilities"},
    ]
    programs.extend(system_apps)
    
    print(f"✅ Найдено {len(programs)} программ")
    return programs


def categorize_apps(apps):
    """Категоризирует приложения"""
    categories = {
        "office": ["word", "excel", "outlook", "powerpoint", "access", "onenote"],
        "browser": ["chrome", "firefox", "edge", "opera", "brave", "browser"],
        "messenger": ["telegram", "whatsapp", "skype", "discord", "slack", "teams"],
        "media": ["vlc", "spotify", "itunes", "media"],
        "development": ["visual", "code", "studio", "python", "git", "docker"],
        "utilities": ["calculator", "notepad", "paint", "snipping", "clock"]
    }
    
    for app in apps:
        name_lower = app.get("name", "").lower()
        app["category"] = "other"
        for cat, keywords in categories.items():
            if any(kw in name_lower for kw in keywords):
                app["category"] = cat
                break
    return apps


def main():
    print("="*60)
    print("  🚀 УМНЫЙ СКАНЕР СИСТЕМЫ И СЕТИ")
    print("="*60)
    print()
    
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)
    
    # 1. Сканируем программы
    print("📦 ЧАСТЬ 1: Программы")
    print("-" * 40)
    programs = scan_registry_programs()
    programs = categorize_apps(programs)
    
    # 2. Сканируем сеть
    print("\n🌐 ЧАСТЬ 2: Сетевые ресурсы")
    print("-" * 40)
    
    # Находим компьютеры в сети
    computers = find_network_computers()
    
    # Сканируем все найденные ресурсы
    documents = scan_all_network_resources(computers)
    
    # 3. Создаем итоговый индекс
    print("\n Формирование индекса...")
    
    # Группируем документы по источникам
    docs_by_source = {}
    for doc in documents:
        source = doc.pop("source", "Неизвестно")
        if source not in docs_by_source:
            docs_by_source[source] = []
        docs_by_source[source].append(doc)
    
    # Группируем программы по категориям
    apps_by_category = {}
    for app in programs:
        cat = app.get("category", "other")
        if cat not in apps_by_category:
            apps_by_category[cat] = []
        apps_by_category[cat].append(app)
    
    index_data = {
        "metadata": {
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "computer_name": os.environ.get("COMPUTERNAME", "Unknown"),
            "total_apps": len(programs),
            "total_docs": len(documents),
            "network_computers": computers,
            "local_shares": [s["name"] for s in find_local_shares()],
            "network_drives": [d["name"] for d in find_network_drives()]
        },
        "apps": {
            "by_category": apps_by_category,
            "all": programs
        },
        "documents": {
            "by_source": docs_by_source,
            "all": documents
        }
    }
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("  🎉 ИНДЕКС СОЗДАН!")
    print("="*60)
    print(f"📁 Файл: {INDEX_FILE}")
    print(f"📦 Программ: {len(programs)}")
    print(f"📄 Документов: {len(documents)}")
    print(f" Компьютеров в сети: {len(computers)}")
    print(f"\nТеперь агент 'Альфа' знает всю систему!")


if __name__ == "__main__":
    main()