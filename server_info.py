# ---------------------------------------------------------------------------------
# Name: ServerInfo
# Description: Получение информации о сервере
# meta developer: @kompot_69
# ---------------------------------------------------------------------------------

__version__ = (2,0)
from .. import loader, utils
import logging
import psutil
import os
import subprocess
import pwd
import re
import json

logger = logging.getLogger(__name__)

# [ PREFIX ]
def set_prefix(cfg_percents,percent):
    try:
        match percent:
            case p if p > cfg_percents[2]: return "🔴"
            case p if p > cfg_percents[1]: return "🟠"
            case p if p > cfg_percents[0]: return "🟡" 
            case p if p < 0: return "❓" 
            case _: return "🟢"
    except Exception as err: return f'<b>overload_percents config error:</b> \n<code>{err}</code>\n'
def set_service_prefix(status):
    match status:
        case 'active': return "🟢"
        case 'inactive': return "🟡"
        case 'unknown': return "❓"
        case _: return "🔴"

# [ SYSTEM USAGE ]
def size_count(bytes_per_unit, bytes):
    bytes= bytes / (bytes_per_unit * bytes_per_unit) # b > mb
    if bytes > (bytes_per_unit*bytes_per_unit): return f'{bytes / bytes_per_unit / bytes_per_unit:.1f}TB' # if bytes > 1 TB
    elif bytes > bytes_per_unit: return f'{bytes / bytes_per_unit:.1f}GB' # if bytes > 1 GB
    else: return f'{bytes:.1f}MB'
def get_uptime():
    try: return subprocess.check_output(['uptime', '-p']).decode().strip()[3:]
    except Exception as e: return f'\nError: {e}'
def get_ip():
    try: ext_ip = subprocess.check_output(['curl', '-s', 'https://api64.ipify.org']).decode().strip()
    except Exception: ext_ip = 'unknown'
    try: int_ip = subprocess.check_output(['hostname', '-I']).decode().strip()
    except Exception: int_ip = 'unknown'
    return ext_ip,int_ip
def get_ports_processes(ext_ip=None,int_ip=None):
    try:
        result_text=""
        lines = subprocess.check_output(['lsof', '-i', '-P', '-n'], text=True).splitlines()
        for line in lines[1:]: 
            columns = line.split()
            if len(columns) >= 9 and 'LISTEN' in columns[-1]:
                command = columns[0]
                address = columns[8]
                if ':' in address:
                    port = address.rsplit(':', 1)[-1]
                    new_line=f"\n {port} - {command}"
                    if ext_ip and int_ip: new_line += f"   ( <a href='{ext_ip}:{port}'>Ext</a> | <a href='{int_ip}:{port}'>Int</a> )"
                    if new_line not in result_text: result_text += new_line
        return result_text
    except subprocess.CalledProcessError as e: return ("Ошибка:", e)
    except FileNotFoundError: return "Команда lsof не найдена."
def get_services_status(services):
    try:
        result_text=''
        for service in services:
            try: status = subprocess.check_output(['systemctl', 'is-active', service+".service"]).decode().strip()
            except subprocess.CalledProcessError: status = 'unknown'
            result_text += f'\n{set_service_prefix(status)} {service}: {status}'
        try: 
            failed_services = json.loads(subprocess.check_output(['systemctl', 'list-units', '--failed', '-o', 'json-pretty']).decode().strip())
            for service in failed_services: 
                result_text +='\n🔴 '+service['unit']
        except Exception as e: result_text += f'\nError: {e}'
        return result_text
    except Exception as e: return f'\nError: {e}'
def get_cpu_load(average=False): 
    try:
        if average: return [round(val, 1) for val in os.getloadavg()]
        else: return psutil.cpu_percent(interval=1)
    except Exception: return 'unknown'
def get_memory_info(bytes_per_unit):
    try:
        mem = psutil.virtual_memory()
        return mem.percent, size_count(bytes_per_unit, mem.used), size_count(bytes_per_unit, mem.total), size_count(bytes_per_unit, mem.free)
    except Exception: return 'unknown','-','-','-'
def get_disk_info(bytes_per_unit):
    try:
        partitions = psutil.disk_partitions()
        disk_info = {}
        for partition in partitions:
            usage = psutil.disk_usage(partition.mountpoint)
            free_display = size_count(bytes_per_unit, usage.free)
            total_display = size_count(bytes_per_unit, usage.total)
            used_display = size_count(bytes_per_unit, usage.used)
            disk_info[partition.device] = {
                'free': free_display,
                'total': total_display,
                'used': used_display,
                'used_percent': usage.percent
            }
        return disk_info
    except Exception: return 'unknown'

# [ CONFIGURATION COMPONENTS INFO ]
def get_os_info():
    try: return [line.split('=')[1].strip().strip('"') for line in subprocess.check_output(['cat', '/etc/os-release']).decode().splitlines() if line.startswith('PRETTY_NAME=')][0]
    except Exception: return 'unknown'
def get_motherboard_info():
    try:
        output = subprocess.check_output(['sudo', 'dmidecode', '-t', 'baseboard']).decode()
        manufacturer = re.search(r'Manufacturer: (.+)', output)
        model = re.search(r'Product Name: (.+)', output)
        return manufacturer.group(1), model.group(1)
    except PermissionError : return 'PermissionError', '-'
    except Exception: return 'unknown', '-'
def get_cpu_info():
    try:
        output = subprocess.check_output(['lscpu']).decode()
        model = re.search(r'Model name:\s+(.+)', output).group(1)
        return model
    except PermissionError : return 'PermissionError'
    except Exception: return 'unknown'
def get_gpu_info():
    try:
        output = subprocess.check_output(['lspci', '-vnn']).decode()
        matches = re.findall(r'VGA compatible controller.*?\n\s+Subsystem: (.*?)\n.*?Memory at [\da-f]+ \((\d+)MB\)', output, re.DOTALL)
        gpus = [(m[0]) for m in matches]
        return gpus if gpus else [('unknown','')]
    except PermissionError : return [('PermissionError','')]
    except Exception: return [('unknown','')]
def get_ram_info(): 
    try:
        ram=''
        output = subprocess.check_output(['sudo', 'dmidecode', '-t', 'memory']).decode()
        blocks = []
        current_block = None
        for line in output.split('\n'):
            stripped_line = line.strip()
            if stripped_line.startswith("Handle") and "DMI type 17" in stripped_line:
                current_block = {}
                blocks.append(current_block)
            elif current_block is not None:
                if stripped_line.startswith("Size:"): current_block["Size"] = stripped_line.split(":", 1)[1].strip()
                elif stripped_line.startswith("Type:"): current_block["Type"] = stripped_line.split(":", 1)[1].strip()
                elif stripped_line.startswith("Speed:"): current_block["Speed"] = stripped_line.split(":", 1)[1].strip()
                elif stripped_line.startswith("Part Number:"): current_block["Part Number"] = stripped_line.split(":", 1)[1].strip()
        for i, block in enumerate(blocks, 1):
            ram+=f"\n<b>RAM:</b> {block.get('Size', 'N/A')} {block.get('Type', 'N/A')} {block.get('Speed', 'N/A')} <code>{block.get('Part Number', 'N/A')}</code>"
        return ram    
    except PermissionError: return [('PermissionError', '-', '-', '-')]
    except Exception: return [('unknown', '-', '-', '-')]
def get_disk_conf_info():
    try:
        output = subprocess.check_output(['lsblk', '-d', '-o', 'NAME,MODEL,SIZE,ROTA']).decode()
        disks = []
        for line in output.split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 4:
                name, model, size, rota = parts[0], ' '.join(parts[1:-2]), parts[-2], parts[-1]
                disk_type = 'HDD' if rota == '1' else 'SSD'
                disks.append((model, size, disk_type))
        return disks if disks else [('unknown', '-', '-')]
    except PermissionError: return [('PermissionError', '-', '-')]
    except Exception: return [('unknown', '-', '-')]


@loader.tds
class ServerInfoMod(loader.Module):
    """server info by @kompot_69 & ChatGPT"""
    
    allowed_args = {
      "config":"server components info",
      "usage":"[-f] server resources usage info",
      "services":"services monitoring",
      "ports":"[-ip] ports usage monitoring"
    }
    
    strings = {
        "name": "ServerInfo",
        "services_info_text": "<i>ℹ You can change services list in the config</i>",
        "_cfg_services_list": "services check list",
        "_cfg_overload_percents": "overload percents (🟡🟠🔴)",
        "_cfg_bytes_per_unit": "bytes per unit (1000 or 1024)",
        "_cfg_ports_show_ip": "show IP in ports <i>info</i> (can switch by -ip key)",
        "_cfg_extended_view": "extended view in <i>usage</i> (can switch by -f key)",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "ports_show_ip",
                True,
                lambda m: self.strings["_cfg_ports_show_ip"],
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "extended_view",
                True,
                lambda m: self.strings["_cfg_extended_view"],
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "services_list",
                "hikka,ssh",
                lambda m: self.strings["_cfg_services_list"],
            ),
            loader.ConfigValue(
                "overload_percents",
                "60,75,90",
                lambda m: self.strings["_cfg_overload_percents"],
            ),
            loader.ConfigValue(
                "bytes_per_unit",
                "1000",
                lambda m: self.strings["_cfg_bytes_per_unit"],
            ),
        )
        self.name = self.strings["name"]
        self.services_info_text = self.strings["services_info_text"]

    
    async def servercmd(self, message):
        """[ports|services|usage|config]"""
        args = utils.get_args_raw(message).lower().split(" ")
        info_text=''
        
        if not any(arg in self.allowed_args for arg in args):
          info_text=f'<b>{self.name}</b> module usage:'
          for arg, arg_descript in self.allowed_args.items():
            info_text+=f'\n <code>server {arg}</code> - {arg_descript}'
          return await utils.answer(message, info_text)
        
        await utils.answer(message, f'<b>[{self.name}]</b>\ngetting info...')
        
        for arg in args: 
          if arg == 'config': pass
            
        if "config" in args: 
          info_text+='<b>Config:</b>'
          info_text+=f'\n<b>OS:</b> {get_os_info()}'
          mb_manufacturer, mb_model = get_motherboard_info()
          info_text+=f'\n<b>Motherboard:</b> {mb_manufacturer} <code>{mb_model}</code>'
          info_text+=f'\n<b>CPU:</b> <code>{get_cpu_info()}</code>'
          for gpu in get_gpu_info(): info_text+=f'\n<b>GPU:</b> <code>{gpu[0]}</code>'
          info_text+=f"{get_ram_info()}"
          for disk in get_disk_conf_info(): info_text+=f'\n<b>{disk[2]}:</b> {disk[1]} <code>{disk[0]}</code>'
          info_text+="\n\n"
          
        if "usage" in args:
          info_text+='<b>Usage:</b>'
          percents = self.config["overload_percents"]
          bytes_per_unit = self.config["bytes_per_unit"]
          extended_view = self.config["extended_view"]
          if "-f" in args: extended_view=not extended_view 
          info_text+=f'\n<b>Uptime:</b> {get_uptime()}'
          cpu_load=get_cpu_load()
          info_text+=f'\n{set_prefix(percents,cpu_load)} <b>CPU:</b> {cpu_load}%\n'
          if extended_view: info_text+=f'<b> └ 1m, 5m, 15m :</b> {get_cpu_load(average=True)}\n'
          mem_percent, mem_used, mem_total, mem_free = get_memory_info(bytes_per_unit)
          if extended_view: info_text+=f'{set_prefix(percents,mem_percent)} <b>RAM:</b> {mem_percent}%\n<b> ├ free:</b> {mem_free} of {mem_total}\n<b> └ used:</b> {mem_used}\n'
          else: info_text+=f'{set_prefix(percents,mem_percent)} <b>RAM:</b> {mem_percent}% - used {mem_used} of {mem_total}\n'
          for disk, info in get_disk_info(bytes_per_unit).items():
              if extended_view: info_text+=f'{set_prefix(percents,info["used_percent"])} <b>{disk} :</b> {info["used_percent"]}% \n<b> ├ free:</b> {info["free"]} of {info["total"]}\n<b> └ used:</b> {info["used"]}\n'
              else: info_text+=f'{set_prefix(percents,info["used_percent"])} {disk} - used {info["used_percent"]}%, free: {info["free"]}\n'
          info_text+="\n\n"
          
        if "services" in args: 
          info_text+='<b>Services:</b>'
          services = self.config["services_list"].replace(" ", "").split(",")
          if not services or services == ["hikka","ssh"]: info_text+=f"\n{self.services_info_text}"
          info_text+=get_services_status(services)
          info_text+="\n\n"
          
        if "ports" in args: 
          info_text+='<b>Ports:</b>'
          show_ip = self.config["ports_show_ip"] if "-ip" not in args else not self.config["ports_show_ip"]
          if show_ip: 
            ext_ip,int_ip=get_ip()
            info_text+=f'\n<b>Ext. IP:</b> <code>{ext_ip}</code>\n<b>Int. IP:</b> <code>{int_ip}</code>'
            info_text+=get_ports_processes(ext_ip,int_ip)
          else: info_text+=get_ports_processes()
          info_text+="\n\n"
          
        await utils.answer(message, f"<b>[{self.name}]</b> {info_text}")
