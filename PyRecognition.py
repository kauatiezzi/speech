import os
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import threading
from queue import Queue, Empty

class PyRecognition:
    def __init__(self, language):
        self.language = language
        self.driver = None
        self.speech_queue = Queue()
        self.is_running = False
        self.recognition_thread = None
        self.POLL_INTERVAL = 0.03  # Leitura bem rápida

        self._setup_driver()
        self._start_recognition_loop()

    def _setup_driver(self):
        """Configura o driver do Chrome com otimizações"""
        path = './chromedriver.exe'
        options = Options()
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-background-media-suspend')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2,
        })
        
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        options.add_argument('--window-size=300,200')
        options.add_argument('--window-position=0,0')

        service = Service(path)
        
        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(1)
            self.driver.set_page_load_timeout(10)
            
            engine_path = Path(os.getcwd()).joinpath('Engine', 'engine.html').resolve()
            self.driver.get(engine_path.as_uri())
            
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.ID, "lg")))
            self.driver.execute_script(f"document.getElementById('lg').innerHTML = '{self.language}';")
            
            wait.until(EC.presence_of_element_located((By.ID, "resultSpeak")))
            time.sleep(0.5)
            
            print(f"PyRecognition inicializado com sucesso! Idioma: {self.language}")
            
        except Exception as e:
            print(f"Erro ao inicializar PyRecognition: {e}")
            if self.driver:
                self.driver.quit()
            raise

    def _start_recognition_loop(self):
        """Inicia o loop de reconhecimento em thread separada"""
        self.is_running = True
        self.recognition_thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.recognition_thread.start()

    def _recognition_loop(self):
        """Loop que apenas lê o texto do HTML e o envia."""
        last_speech = ""
        while self.is_running:
            try:
                if not self.driver:
                    break
                
                speech_element = self.driver.find_element(By.ID, "resultSpeak")
                speech = speech_element.text
                
                # Envia a transcrição se ela mudou.
                if speech != last_speech:
                    self.speech_queue.put(speech)
                    last_speech = speech

                time.sleep(self.POLL_INTERVAL)
            except Exception:
                # Em caso de erro (ex: browser fechando), apenas espera um pouco
                time.sleep(0.1)

    def get_all_pending(self):
        """Retorna todos os comandos pendentes"""
        results = []
        while not self.speech_queue.empty():
            try:
                result = self.speech_queue.get_nowait()
                results.append(result)
            except Empty:
                break
        return results

    def stop(self):
        """Para o reconhecimento e fecha recursos"""
        self.is_running = False
        
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=1)
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        print("PyRecognition finalizado.")

    def __del__(self):
        """Destrutor para limpeza automática"""
        self.stop()