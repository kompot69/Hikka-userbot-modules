# ахтунг! говнокод!
# by @kompot_69
__version__ = (1, 2)
from .. import loader, utils
import logging
import psutil
import os
import subprocess
import re
import json

logger = logging.getLogger(__name__)

# [ INFORMATION ]
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
def get_load_average():
    load_avg = os.getloadavg()
    return [round(val, 1) for val in load_avg]
def get_memory_info(bytes_per_unit):
    mem = psutil.virtual_memory()
    return mem.percent, mem.used // (bytes_per_unit * bytes_per_unit), mem.total // (bytes_per_unit * bytes_per_unit)
def size_count(bytes_per_unit, bytes):
    bytes= bytes / (bytes_per_unit * bytes_per_unit)
    if bytes > (bytes_per_unit*bytes_per_unit): return f'{bytes / bytes_per_unit / bytes_per_unit:.1f}TB' # if bytes > 1 TB
    elif bytes > bytes_per_unit: return f'{bytes / bytes_per_unit:.1f}GB' # if bytes > 1 GB
    else: return f'{bytes}MB'
def get_disk_info(bytes_per_unit):
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
def get_external_ip():
    try: return subprocess.check_output(['curl', '-s', 'https://api64.ipify.org']).decode().strip()
    except Exception: return 'unknown'
def get_service_status(service_name):
    try:
        result = subprocess.check_output(['systemctl', 'is-active', service_name]).decode().strip()
        return result
    except subprocess.CalledProcessError: return 'unknown'
def get_failed_services():
    try:
        result=''
        failed_services = json.loads(subprocess.check_output(['systemctl', 'list-units', '--failed', '-o', 'json-pretty']).decode().strip())
        for service in failed_services: result+='\n🔴 '+service['unit']
        return result
    except Exception: pass

# [ CONFIGURATION ]
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
            # Начало блока Memory Device (DMI type 17)
            if stripped_line.startswith("Handle") and "DMI type 17" in stripped_line:
                current_block = {}
                blocks.append(current_block)
            elif current_block is not None:
                if stripped_line.startswith("Size:"): current_block["Size"] = stripped_line.split(":", 1)[1].strip()
                elif stripped_line.startswith("Type:"): current_block["Type"] = stripped_line.split(":", 1)[1].strip()
                elif stripped_line.startswith("Speed:"): current_block["Speed"] = stripped_line.split(":", 1)[1].strip()
                elif stripped_line.startswith("Part Number:"): current_block["Part Number"] = stripped_line.split(":", 1)[1].strip()
        for i, block in enumerate(blocks, 1):
            ram+=f"\n<b>RAM:</b> <code>{block.get('Part Number', 'N/A')}</code> {block.get('Size', 'N/A')} {block.get('Type', 'N/A')} {block.get('Speed', 'N/A')}"
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
    
    strings = {
        "name": "ServerInfo",
        "_cfg_services_list": "services check list",
        "_cfg_overload_percents": "overload percents (🟡🟠🔴)",
        "_cfg_bytes_per_unit": "bytes per unit (1000 or 1024)",
        "_cfg_show_ip": "show IP in info",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "show_ip",
                True,
                lambda m: self.strings["_cfg_show_ip"],
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
    
    async def serverinfocmd(self, message):
        """[-f|-ip] - server usage & servises status"""
        await utils.answer(message, f'<b>[{self.name}]</b>\ngetting info...')
        info_text=''
        percents = self.config["overload_percents"]
        bytes_per_unit = self.config["bytes_per_unit"]
        show_ip = self.config["show_ip"]
        extended_view = self.config["extended_view"]
        # args
	if "-f" in utils.get_args_raw(message): extended_view=True 
	if "-ip" in utils.get_args_raw(message): show_ip=True 


        uptime=subprocess.check_output(['uptime', '-p']).decode().strip()
        info_text+=f'<b>Uptime:</b> {uptime[3:]} \n'

        if show_ip: info_text+=f'<b>Ext. IP:</b> <code>{get_external_ip()}</code>\n'

        cpu_load=psutil.cpu_percent(interval=1)
        info_text+=f'\n{set_prefix(percents,cpu_load)} <b>CPU:</b> {cpu_load}%\n'
        if extended_view: info_text+=f'<b> └ 1m, 5m, 15m :</b> {get_load_average()}\n'

        mem_percent, mem_used, mem_total = get_memory_info(bytes_per_unit)
        if extended_view: info_text+=f'{set_prefix(percents,mem_percent)} <b>RAM:</b> {mem_percent}%\n'
        else: info_text+=f'{set_prefix(percents,mem_percent)} <b>RAM:</b> {mem_percent}% ({mem_used}MB / {mem_total}MB)\n'
        

        for disk, info in get_disk_info(bytes_per_unit).items():
            if extended_view: info_text+=f'{set_prefix(percents,info["used_percent"])} <b>{disk} :</b> {info["used_percent"]}% \n<b> ├ free:</b> {info["free"]} of {info["total"]}\n<b> └ used:</b> {info["used"]}\n'
            else: info_text+=f'{set_prefix(percents,info["used_percent"])} {disk} - used {info["used_percent"]}%, free: {info["free"]}\n'
            
        info_text+='\n<b>Services:</b>'
        services = self.config["services_list"].replace(" ", "").split(",")
        for service in services:
            status=get_service_status(service+".service")
            info_text+=f'\n{set_service_prefix(status)} {service}: {status}'
        info_text+=get_failed_services()

        await utils.answer(message, info_text)

    async def serverconfigcmd(self, message):
        """ - server components info"""
        await utils.answer(message, f'<b>[{self.name}]</b>\ngetting info...')
        info_text=''
        
        mb_manufacturer, mb_model = get_motherboard_info()
        info_text+=f'\n<b>Motherboard:</b> {mb_manufacturer} <code>{mb_model}</code>'
        info_text+=f'\n<b>CPU:</b> <code>{get_cpu_info()}</code>'
        for gpu in get_gpu_info(): info_text+=f'\n<b>GPU:</b> <code>{gpu[0]}</code>'
        info_text+=f"{get_ram_info()}"
        for disk in get_disk_conf_info(): info_text+=f'\n<b>{disk[2]}:</b> <code>{disk[0]}</code> {disk[1]}'

        await utils.answer(message, info_text)
