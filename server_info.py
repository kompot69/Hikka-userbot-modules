# ---------------------------------------------------------------------------------
# Name: ServerInfo
# Description: Получение информации о сервере (упрощённая версия)
# meta developer: @kompot_69
# ---------------------------------------------------------------------------------

__version__ = (2,1)
from .. import loader, utils
import logging, psutil, os, subprocess, re, json

logger = logging.getLogger(__name__)

# [ PREFIX ]
def set_prefix(cfg_percents, percent):
    try:
        p = percent
        return (
            "🔴" if p > cfg_percents[2] else
            "🟠" if p > cfg_percents[1] else
            "🟡" if p > cfg_percents[0] else
            "❓" if p < 0 else "🟢"
        )
    except Exception as err:
        return f'<b>overload_percents config error:</b> \n<code>{err}</code>\n'

def set_service_prefix(status):
    return {
        'active': "🟢",
        'inactive': "🟡",
        'unknown': "❓"
    }.get(status, "🔴")

# [ SYSTEM USAGE ]
def size_count(bytes_per_unit, bytes):
    bytes /= bytes_per_unit ** 2 # b to mb
    return (
        f'{bytes/bytes_per_unit**2:.1f}TB' if bytes > bytes_per_unit ** 2 else
        f'{bytes/bytes_per_unit:.1f}GB' if bytes > bytes_per_unit else
        f'{bytes:.1f}MB'
    )
    
def get_uptime():
    try: return subprocess.check_output(['uptime', '-p']).decode().strip()[3:]
    except: return 'unknown'

def get_ip():
    try: ext = subprocess.check_output(['curl', '-s', 'https://api64.ipify.org']).decode().strip()
    except: ext = 'unknown'
    try: intr = subprocess.check_output(['hostname', '-I']).decode().strip()
    except: intr = 'unknown'
    return ext, intr

def get_ports_processes(ip=None):
    try:
      result_text = "\n<b>open | proto | port | process</b>\n" if ip else "\n<b>proto | port | process</b>\n"
      seen = {}
      lines = subprocess.check_output('ss -p -l -n', shell=True, text=True).splitlines()
      for line in lines:
        if not line or not any(proto in line for proto in ('tcp', 'udp')): continue
        cols = line.split()
        proto = cols[0]
        local = cols[4]
        port = local.split(':')[-1]
        match = re.search(r'\"(.+?)\"', line)
        proc = match.group(1) if match else '?'
        key = (port, proc)
        if key in seen: seen[key].add(proto)
        else: seen[key] = {proto}
      for (port, proc), protos in sorted(seen.items(), key=lambda x: (int(x[0][0]), x[0][1])):
        for p in (sorted(protos) if len(protos) == 1 else [' - ']):
          if ip: result_text += f"  <a href='{ip}:{port}'> 🌐 </a> | "
          while len(port)<4: port=' '+port
          result_text += f" <code>{p}</code>  | <code>{port}</code> | <code>{proc}</code> \n"
          break
      return result_text
    except Exception as e: return f"Ошибка: {e}"
        
def get_services_status(services):
    out = ''
    for s in services:
        try:
            status = subprocess.check_output(['systemctl', 'is-active', s + ".service"]).decode().strip()
        except subprocess.CalledProcessError:
            status = 'unknown'
        out += f'\n{set_service_prefix(status)} {s}: {status}'
    try:
        failed = json.loads(subprocess.check_output(['systemctl', 'list-units', '--failed', '-o', 'json-pretty']).decode())
        for svc in failed:
            unit = svc['unit']
            if unit.endswith('.service'):
                out += f'\n🔴 {unit} (FAILED)'
    except Exception:
        pass
    return out

def get_cpu_load(avg=False):
    try: return [round(v,1) for v in os.getloadavg()] if avg else psutil.cpu_percent(interval=1)
    except: return 'unknown'

def get_memory_info(unit):
    try:
        mem = psutil.virtual_memory()
        return mem.percent, size_count(unit, mem.used), size_count(unit, mem.total), size_count(unit, mem.free)
    except: return 'unknown', '-', '-', '-'

def get_disk_info(unit):
    try:
        info = {}
        for part in psutil.disk_partitions():
            usage = psutil.disk_usage(part.mountpoint)
            info[part.device] = {
                'free': size_count(unit, usage.free),
                'total': size_count(unit, usage.total),
                'used': size_count(unit, usage.used),
                'used_percent': usage.percent
            }
        return info
    except: return 'unknown'

# [ CONFIGURATION COMPONENTS INFO ]
def get_os_info():
    try:
        return next(line.split('=')[1].strip('"') for line in subprocess.check_output(['cat', '/etc/os-release']).decode().splitlines() if line.startswith('PRETTY_NAME='))
    except: return 'unknown'

def get_motherboard_info():
    try:
        output = subprocess.check_output(['sudo', 'dmidecode', '-t', 'baseboard']).decode()
        man = re.search(r'Manufacturer: (.+)', output)
        model = re.search(r'Product Name: (.+)', output)
        return man.group(1), model.group(1)
    except PermissionError: return 'PermissionError', '-'
    except: return 'unknown', '-'

def get_cpu_info():
    try: return re.search(r'Model name:\s+(.+)', subprocess.check_output(['lscpu']).decode()).group(1)
    except PermissionError: return 'PermissionError'
    except: return 'unknown'
    
def get_gpu_info():
    try:
        out = subprocess.check_output(['lspci', '-vnn']).decode()
        matches = re.findall(r'(?:VGA compatible controller|3D controller).*?Subsystem: (.*?)\n', out, re.DOTALL)
        results = []
        for line in matches:
            if any(x in line.lower() for x in ['llvmpipe', 'integrated', 'cpu']):
                continue  # встроенные/программные
            results.append((line.strip(), ''))
        return results
    except: return []

def get_ram_info():
    try:
        output = subprocess.check_output(['sudo', 'dmidecode', '-t', 'memory']).decode()
        ram, block, out = '', None, []
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith("Handle") and "DMI type 17" in line:
                block = {}
                out.append(block)
            elif block is not None:
                for field in ("Size", "Type", "Speed", "Part Number"):
                    if line.startswith(field + ":"):
                        block[field] = line.split(":", 1)[1].strip()
        for b in out:
            ram += f"\n<b>RAM:</b> {b.get('Size','N/A')} {b.get('Type','N/A')} {b.get('Speed','N/A')} <code>{b.get('Part Number','N/A')}</code>"
        return ram
    except PermissionError: return [('PermissionError', '-', '-', '-')]
    except: return [('unknown', '-', '-', '-')]

def get_disk_conf_info():
    try:
        output = subprocess.check_output(['lsblk', '-d', '-o', 'NAME,MODEL,SIZE,ROTA']).decode()
        disks = []
        for line in output.split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 4:
                name, model, size, rota = parts[0], ' '.join(parts[1:-2]), parts[-2], parts[-1]
                disks.append((model, size, 'HDD' if rota == '1' else 'SSD'))
        return disks if disks else [('unknown', '-', '-')]
    except PermissionError: return [('PermissionError', '-', '-')]
    except: return [('unknown', '-', '-')]

@loader.tds
class ServerInfoMod(loader.Module):
    """server info by @kompot_69 & ChatGPT"""

    allowed_args = {
        "config": "server components info",
        "usage": "server resources usage info\n   [-f show/hide full info]",
        "services": "services monitoring",
        "ports": "ports usage monitoring\n   [-i show/hide ip]\n   [-g show global ip open button]\n   [-l show local ip open button]"
    }

    strings = {
        "name": "ServerInfo",
        "services_info_text": "<i>ℹ You can change services list in the config</i>",
        "_cfg_services_list": "services check list",
        "_cfg_overload_percents": "overload percents (🟡🟠🔴)",
        "_cfg_bytes_per_unit": "bytes per unit (1000 or 1024)",
        "_cfg_ports_show_ip": "show IP in ports <i>info</i> (can switch by -i key)",
        "_cfg_extended_view": "extended view in <i>usage</i> (can switch by -f key)",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("ports_show_ip", True, lambda m: self.strings["_cfg_ports_show_ip"], validator=loader.validators.Boolean()),
            loader.ConfigValue("extended_view", True, lambda m: self.strings["_cfg_extended_view"], validator=loader.validators.Boolean()),
            loader.ConfigValue("services_list", "hikka,ssh", lambda m: self.strings["_cfg_services_list"]),
            loader.ConfigValue("overload_percents", "60,75,90", lambda m: self.strings["_cfg_overload_percents"]),
            loader.ConfigValue("bytes_per_unit", "1000", lambda m: self.strings["_cfg_bytes_per_unit"]),
        )
        self.name = self.strings["name"]
        self.services_info_text = self.strings["services_info_text"]

    async def servercmd(self, message):
        """[ports|services|usage|config]"""
        args = utils.get_args_raw(message).lower().split()
        if not any(arg in self.allowed_args for arg in args):
            return await utils.answer(message, f'<b>{self.name}</b> module usage:' + ''.join(f'\n <code>server {k}</code> - {v}' for k,v in self.allowed_args.items()))

        await utils.answer(message, f'<b>[{self.name}]</b>\ngetting info...')
        info = ''

        if "config" in args:
            info += '<b>Config:</b>'
            info += f'\n<b>OS:</b> {get_os_info()}'
            mb_man, mb_mod = get_motherboard_info()
            info += f'\n<b>Motherboard:</b> {mb_man} <code>{mb_mod}</code>'
            info += f'\n<b>CPU:</b> <code>{get_cpu_info()}</code>'
            gpus = get_gpu_info()
            if gpus:
                for gpu in gpus:
                    info += f'\n<b>GPU:</b> <code>{gpu[0]}</code>'
            else:
                info += '\n<b>GPU:</b> <code>none</code>'
            info += f"{get_ram_info()}"
            for disk in get_disk_conf_info(): info += f'\n<b>{disk[2]}:</b> {disk[1]} <code>{disk[0]}</code>'
            info += "\n\n"

        if "usage" in args:
            info += '<b>Usage:</b>'
            try:
                percents = list(map(int, str(self.config["overload_percents"]).split(",")))
            except: percents = [60, 75, 90]
            try: unit = int(self.config["bytes_per_unit"])
            except: unit = 1000
            ext = not ("-f" in args) if self.config["extended_view"] else ("-f" in args)
            info += f'\n<b>Uptime:</b> {get_uptime()}'
            cpu = get_cpu_load()
            info += f'\n{set_prefix(percents,cpu)} <b>CPU:</b> {cpu}%\n'
            if ext: info += f'<b> └ 1m, 5m, 15m :</b> {get_cpu_load(avg=True)}\n'
            mem_p, mem_u, mem_t, mem_f = get_memory_info(unit)
            info += (
                f'{set_prefix(percents,mem_p)} <b>RAM:</b> {mem_p}%\n<b> ├ free:</b> {mem_f} of {mem_t}\n<b> └ used:</b> {mem_u}\n' if ext else
                f'{set_prefix(percents,mem_p)} <b>RAM:</b> {mem_p}% - used {mem_u} of {mem_t}\n'
            )
            for d, i in get_disk_info(unit).items():
                info += (
                    f'{set_prefix(percents,i["used_percent"])} <b>{d} :</b> {i["used_percent"]}% \n<b> ├ free:</b> {i["free"]} of {i["total"]}\n<b> └ used:</b> {i["used"]}\n' if ext else
                    f'{set_prefix(percents,i["used_percent"])} {d} - used {i["used_percent"]}%, free: {i["free"]}\n'
                )
            info += "\n\n"

        if "services" in args:
            info += '<b>Services:</b>'
            services = self.config["services_list"].replace(" ", "").split(",")
            if not services or services == ["hikka","ssh"]:
                info += f"\n{self.services_info_text}"
            info += get_services_status(services) + "\n\n"

        if "ports" in args:
            info += '<b>Ports usage:</b>'
            ext_ip, int_ip = get_ip()
            if self.config["ports_show_ip"] != ("-i" in args):
              info += f'\n<b>Ext. IP:</b> <code>{ext_ip}</code>\n<b>Int. IP:</b> <code>{int_ip}</code>'
            if "-g" in args: info += str(get_ports_processes(ext_ip))
            elif "-l" in args: info += str(get_ports_processes(int_ip))
            else: info += str(get_ports_processes())
        
        await utils.answer(message, f"<b>[{self.name}]</b> {info}")

