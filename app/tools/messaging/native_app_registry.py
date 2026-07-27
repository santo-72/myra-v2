import os
import shutil
import subprocess
import structlog
from typing import Optional, List, Dict

logger = structlog.get_logger(__name__)

NATIVE_APP_CONFIG: Dict[str, List[str]] = {
    "whatsapp": [
        r"%LOCALAPPDATA%\Programs\WhatsApp\WhatsApp.exe",
        r"%PROGRAMFILES%\WhatsApp\WhatsApp.exe",
        r"%PROGRAMFILES(X86)%\WhatsApp\WhatsApp.exe",
        r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
        "WhatsApp.exe",
        "whatsapp"
    ],
    "messenger": [
        r"%LOCALAPPDATA%\Programs\Messenger\Messenger.exe",
        r"%PROGRAMFILES%\Messenger\Messenger.exe",
        r"%PROGRAMFILES(X86)%\Messenger\Messenger.exe",
        "Messenger.exe",
        "messenger"
    ],
    "telegram": [
        r"%APPDATA%\Telegram Desktop\Telegram.exe",
        r"%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe",
        r"%PROGRAMFILES%\Telegram Desktop\Telegram.exe",
        r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe",
        "Telegram.exe",
        "telegram-desktop",
        "telegram"
    ]
}

UWP_PROTOCOL_MAP = {
    "whatsapp": "whatsapp:",
    "messenger": "messenger:",
    "telegram": "tg:"
}

UWP_AUMID_MAP = {
    "whatsapp": "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
    "telegram": "TelegramMessengerLLP.TelegramDesktop_1t677n0215gvt!Telegram.TelegramDesktop.Store",
    "messenger": "FACEBOOK.317180B0BB486_8xx8rvfyw5nnt!App"
}

def find_native_app_path(app_name: str) -> Optional[str]:
    """
    Checks whether a native desktop application for the requested messaging platform
    is installed on the local system. Supports traditional Windows desktop binaries (.exe),
    Microsoft Store/UWP applications via AppUserModelId (AUMID), and custom protocol schemas.
    Returns the launchable target string or None if not found.
    """
    clean_name = app_name.strip().lower()
    logger.info("checking_native_app_installation", app=clean_name)
    
    # 1. Check UWP / Microsoft Store applications on Windows Registry & Protocol handlers first
    if os.name == "nt":
        try:
            import winreg
            scheme = UWP_PROTOCOL_MAP.get(clean_name)
            if scheme:
                scheme_key = scheme.rstrip(":")
                for root_key, root_name in [(winreg.HKEY_CLASSES_ROOT, "HKCR"), (winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")]:
                    sub_key = scheme_key if root_key == winreg.HKEY_CLASSES_ROOT else f"SOFTWARE\\Classes\\{scheme_key}"
                    try:
                        logger.debug("checking_registry_uwp_protocol", app=clean_name, key=f"{root_name}\\{sub_key}")
                        with winreg.OpenKey(root_key, sub_key) as k:
                            # Check if valid protocol registration exists
                            is_protocol = False
                            try:
                                winreg.QueryValueEx(k, "URL Protocol")
                                is_protocol = True
                            except Exception:
                                try:
                                    val, _ = winreg.QueryValueEx(k, "")
                                    if val and ("url:" in str(val).lower() or scheme_key in str(val).lower()):
                                        is_protocol = True
                                except Exception:
                                    pass
                            
                            if is_protocol:
                                aumid = UWP_AUMID_MAP.get(clean_name)
                                launch_target = f"shell:AppsFolder\\{aumid}" if aumid else scheme
                                logger.info("native_app_found_via_uwp_registry", app=clean_name, launch_target=launch_target, method="uwp_protocol_registry")
                                return launch_target
                    except Exception as e_reg:
                        logger.debug("uwp_protocol_not_present_in_root", app=clean_name, key=f"{root_name}\\{sub_key}", detail=str(e_reg))
        except Exception as e_winreg:
            logger.error("error_checking_uwp_registry", error=str(e_winreg), exc_info=True)

    # 2. Check filesystem candidate executable paths and PATH variables
    candidates = NATIVE_APP_CONFIG.get(clean_name, [])
    for candidate in candidates:
        expanded_path = os.path.expandvars(candidate)
        logger.debug("checking_filesystem_candidate", app=clean_name, candidate=candidate, expanded=expanded_path)
        if os.path.isabs(expanded_path) or ("%" not in expanded_path and (r"\\" in expanded_path or "/" in expanded_path)):
            if os.path.exists(expanded_path) and os.path.isfile(expanded_path):
                logger.info("native_app_found_at_path", app=clean_name, path=expanded_path, method="filesystem")
                return expanded_path
        else:
            which_path = shutil.which(expanded_path)
            if which_path:
                logger.info("native_app_found_in_path", app=clean_name, path=which_path, method="system_path")
                return which_path

    # 3. Check traditional Windows Registry App Paths
    if os.name == "nt":
        try:
            import winreg
            reg_keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths", "HKLM"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths", "HKCU")
            ]
            exec_names = {
                "whatsapp": "WhatsApp.exe",
                "messenger": "Messenger.exe",
                "telegram": "Telegram.exe"
            }
            exe_name = exec_names.get(clean_name)
            if exe_name:
                for root_key, sub_key, root_name in reg_keys:
                    full_key = f"{sub_key}\\{exe_name}"
                    try:
                        logger.debug("checking_registry_app_paths", app=clean_name, key=f"{root_name}\\{full_key}")
                        with winreg.OpenKey(root_key, full_key) as k:
                            val, _ = winreg.QueryValueEx(k, "")
                            if val and os.path.exists(val):
                                logger.info("native_app_found_via_registry_app_path", app=clean_name, path=val, method="registry_app_path")
                                return val
                    except Exception as ex_app:
                        logger.debug("registry_app_path_not_found", app=clean_name, key=f"{root_name}\\{full_key}", error=str(ex_app))
        except Exception as ex_reg:
            logger.error("error_checking_registry_app_paths", error=str(ex_reg), exc_info=True)

    logger.info("native_app_not_found", app=clean_name, result=None)
    return None

def launch_native_app(app_path: str) -> bool:
    """
    Launches the found native application via os.startfile (Windows), explorer for protocol/AUMID schemes, or subprocess.Popen.
    Captures and logs exact errors without swallowing exceptions silently.
    """
    logger.info("attempting_launch_native_app", path=app_path, os_name=os.name)
    try:
        if os.name == "nt":
            # On Windows, handle UWP/Store app shell targets or URI protocol schemes
            if app_path.startswith("shell:") or app_path.endswith(":") or "://" in app_path or not os.path.exists(app_path):
                logger.debug("launching_via_startfile_or_explorer", target=app_path)
                try:
                    if hasattr(os, "startfile"):
                        os.startfile(app_path)
                    else:
                        subprocess.Popen(["explorer.exe", app_path], shell=False)
                except Exception as ex_start:
                    logger.warning("os_startfile_failed_trying_explorer_cmd", target=app_path, error=str(ex_start))
                    subprocess.Popen(f'explorer.exe "{app_path}"', shell=True)
            elif hasattr(os, "startfile") and os.path.exists(app_path):
                logger.debug("launching_via_startfile", target=app_path)
                os.startfile(app_path)
            else:
                logger.debug("launching_via_subprocess_popen", target=app_path)
                subprocess.Popen([app_path], shell=False)
        else:
            logger.debug("launching_via_subprocess_popen", target=app_path)
            subprocess.Popen([app_path], shell=False)
            
        logger.info("launched_native_app_successfully", path=app_path)
        return True
    except Exception as e:
        logger.error("launch_native_app_failed", path=app_path, error=str(e), exc_info=True)
        return False
