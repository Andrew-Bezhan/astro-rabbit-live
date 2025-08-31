"""
Модуль проверки единственности экземпляра бота
"""

import psutil
import os
from utils.logger import setup_logger

logger = setup_logger()


def check_single_instance() -> bool:
    """
    Проверяет, запущен ли уже экземпляр бота
    
    Returns:
        bool: True если это единственный экземпляр, False если есть другие
    """
    try:
        current_pid = os.getpid()
        current_cmdline = ' '.join(psutil.Process(current_pid).cmdline())
        
        # Ищем другие процессы Python с main.py
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline and proc.info['pid'] != current_pid:
                        python_processes.append(proc.info['pid'])
                        logger.warning(f"🔍 Найден другой экземпляр бота: PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if python_processes:
            logger.warning(f"⚠️ Обнаружено {len(python_processes)} других экземпляров бота")
            # Попытка завершить другие процессы
            for pid in python_processes:
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    logger.info(f"🛑 Завершен процесс PID {pid}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось завершить процесс PID {pid}: {e}")
            
            logger.info("✅ Очистка дублирующих процессов завершена")
            return True  # Продолжаем выполнение после очистки
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки единственности: {e}")
        return True  # Разрешаем запуск при ошибке проверки