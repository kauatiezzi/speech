import pygame
import random
import os
import unicodedata
import json
from collections import deque
from PyRecognition import PyRecognition

# --- CONFIGURAÇÕES GERAIS ---
LARGURA_TELA, ALTURA_TELA = 1920, 1080
FPS = 60

# --- INICIALIZAÇÃO PYGAME ---
pygame.init()
pygame.mixer.init()
tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption("Mago dos Comandos - v1.5 Final")
clock = pygame.time.Clock()

# --- ESCALA E PASTAS ---
escala_x, escala_y = LARGURA_TELA / 800.0, ALTURA_TELA / 600.0
pasta_assets = os.path.join(os.path.dirname(__file__), 'assets')
pasta_mago_anim = os.path.join(pasta_assets, 'mago_anim')
pasta_aprendiz_anim = os.path.join(pasta_assets, 'aprendiz_anim')
pasta_monstro_fogo_anim = os.path.join(pasta_assets, 'monstro_fogo_anim')
pasta_monstro_gelo_anim = os.path.join(pasta_assets, 'monstro_gelo_anim')
pasta_monstro_terra_anim = os.path.join(pasta_assets, 'monstro_terra_anim')
pasta_feitico_fogo_anim = os.path.join(pasta_assets, 'feitico_fogo_anim')
pasta_feitico_gelo_anim = os.path.join(pasta_assets, 'feitico_gelo_anim')
pasta_feitico_raio_anim = os.path.join(pasta_assets, 'feitico_raio_anim')
pasta_explosao_anim = os.path.join(pasta_assets, 'explosao_anim')

# --- FONTES ---
tamanho_fonte_grande = int(48 * min(escala_x, escala_y))
tamanho_fonte_pequena = int(24 * min(escala_x, escala_y))
tamanho_fonte_media = int(32 * min(escala_x, escala_y))
fonte = pygame.font.SysFont("Arial", tamanho_fonte_grande, bold=True)
fonte_pequena = pygame.font.SysFont("Arial", tamanho_fonte_pequena)
fonte_media = pygame.font.SysFont("Arial", tamanho_fonte_media, bold=True)

# --- FUNÇÕES AUXILIARES ---
def _normalize_ascii(texto: str) -> str:
    if not texto: return ""
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii').lower()

# --- GERENCIADOR DE PONTUAÇÃO ---
class ScoreManager:
    def __init__(self, filename="scores.json"):
        self.filename = filename
        self.scores = self.load_scores()

    def load_scores(self):
        try:
            with open(self.filename, 'r') as f:
                scores_data = json.load(f)
            # Ordena os scores em ordem decrescente
            return sorted(scores_data, key=lambda x: x['score'], reverse=True)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_score(self, player_name, score):
        self.scores.append({"name": player_name, "score": score})
        # Mantém a lista ordenada após adicionar nova pontuação
        self.scores.sort(key=lambda x: x['score'], reverse=True)
        # Limita a lista para, por exemplo, os 100 melhores scores
        self.scores = self.scores[:100]
        with open(self.filename, 'w') as f:
            json.dump(self.scores, f, indent=4)

    def get_top_scores(self, count=5):
        return self.scores[:count]

# --- GERENCIADOR DE ANIMAÇÕES ---
class AnimationManager:
    def __init__(self):
        self.animations = {}
    def load_animation_from_folder(self, name, path, base_size):
        frames = []
        try:
            files = sorted([f for f in os.listdir(path) if f.endswith('.png')])
            if not files: raise FileNotFoundError(f"Nenhuma imagem em '{path}'")
            for f in files:
                img_path = os.path.join(path, f)
                img = pygame.image.load(img_path).convert_alpha()
                scaled_size = (int(base_size[0] * escala_x), int(base_size[1] * escala_y))
                frames.append(pygame.transform.scale(img, scaled_size))
            self.animations[name] = frames
            print(f"Animação '{name}' carregada: {len(frames)} frames.")
        except Exception as e:
            print(f"ERRO ao carregar '{name}': {e}")
            surf = pygame.Surface((int(base_size[0] * escala_x), int(base_size[1] * escala_y))); surf.fill((255, 0, 255))
            self.animations[name] = [surf]

# --- CARREGAR RECURSOS ---
animation_manager = AnimationManager()
try:
    cenario_img_original = pygame.image.load(os.path.join(pasta_assets, 'cenario.png')).convert()
    # A imagem do cenário agora tem a largura da tela para um loop perfeito
    cenario_img = pygame.transform.scale(cenario_img_original, (LARGURA_TELA, ALTURA_TELA))
except Exception as e:
    print(f"Erro ao carregar cenario.png: {e}")
    cenario_img = pygame.Surface((LARGURA_TELA, ALTURA_TELA)); cenario_img.fill((10,20,50))
cenario_x = 0

# --- CLASSES DE SPRITES ---
class Mago(pygame.sprite.Sprite):
    def __init__(self, anim_manager):
        super().__init__()
        self.anim_manager = anim_manager
        self.animations = {'idle': self.anim_manager.animations.get('mago_idle'), 'cast': self.anim_manager.animations.get('mago_cast')}
        self.current_animation, self.frame_index, self.animation_speed = 'idle', 0.0, 0.1
        self.image = self.animations['idle'][0]
        self.rect = self.image.get_rect(center=(LARGURA_TELA * 0.125, ALTURA_TELA / 2))
        self.casting, self.cast_timer, self.cast_duration = False, 0, 30
    def update(self):
        if self.casting and self.cast_timer > 0:
            self.current_animation = 'cast'; self.cast_timer -= 1
            if self.cast_timer == 0: self.casting = False
        else: self.current_animation = 'idle'
        anim_list = self.animations.get(self.current_animation)
        if anim_list:
            self.frame_index = (self.frame_index + self.animation_speed) % len(anim_list)
            self.image = anim_list[int(self.frame_index)]
    def cast_spell(self):
        self.casting, self.cast_timer, self.frame_index = True, self.cast_duration, 0

class Aprendiz(pygame.sprite.Sprite):
    def __init__(self, mago_referencia, anim_manager, mapa_comandos_voz):
        super().__init__()
        self.anim_manager = anim_manager
        self.mapa_comandos_voz = mapa_comandos_voz
        self.animations = {'idle': self.anim_manager.animations.get('aprendiz_idle')}
        self.current_animation, self.frame_index, self.animation_speed = 'idle', 0.0, 0.1
        if self.animations['idle']:
            self.image = self.animations['idle'][0]
        else:
            print("AVISO: Animação 'aprendiz_idle' não encontrada. Usando placeholder.")
            self.image = pygame.Surface((int(70 * escala_x), int(90 * escala_y))); self.image.fill((0, 255, 255))
        self.image.set_alpha(200)
        self.rect = self.image.get_rect(midbottom=mago_referencia.rect.midtop)
        self.cooldown_tiro, self.cadencia = 0, 480
    def update(self):
        anim_list = self.animations.get(self.current_animation)
        if anim_list:
            self.frame_index = (self.frame_index + self.animation_speed) % len(anim_list)
            self.image = anim_list[int(self.frame_index)]
    def logica_de_combate(self, mago_ref, monstros, sprites, feiticos):
        self.rect.midbottom = mago_ref.rect.midtop; self.rect.y -= 10
        if self.cooldown_tiro > 0: self.cooldown_tiro -= 1
        elif monstros and random.random() <= 0.6:
            alvo = min(monstros, key=lambda m: m.rect.x)
            tipo_feitico = next((f for f, t in self.mapa_comandos_voz.items() if t == alvo.tipo), None)
            if tipo_feitico and alvo.rect.x < LARGURA_TELA:
                # O aprendiz sempre tem um alvo, então passamos o alvo para o construtor
                novo_feitico = Feitico(tipo_feitico, self.rect.center, self.anim_manager, self.mapa_comandos_voz, alvo=alvo)
                sprites.add(novo_feitico); feiticos.add(novo_feitico)
            self.cooldown_tiro = self.cadencia

class Monstro(pygame.sprite.Sprite):
    def __init__(self, dificuldade_atual, anim_manager):
        super().__init__()
        self.anim_manager = anim_manager
        self.tipo = random.choice(["fogo", "gelo", "terra"])
        self.vida_maxima = 1
        if dificuldade_atual > 3 and random.random() < 0.2: self.vida_maxima = 2
        if dificuldade_atual > 6 and random.random() < 0.1: self.vida_maxima = 3
        self.vida_atual = self.vida_maxima
        self.frame_index, self.animation_speed = 0.0, 0.1 + random.uniform(-0.02, 0.02)
        tamanho_base = 80 + (self.vida_maxima - 1) * 20
        frames_base = self.anim_manager.animations[f'monstro_{self.tipo}']
        self.animation_frames = [pygame.transform.scale(f, (int(tamanho_base * escala_x), int(tamanho_base * escala_y))) for f in frames_base]
        self.image = self.animation_frames[0]
        self.rect = self.image.get_rect(x=LARGURA_TELA + 50, y=random.randint(50, ALTURA_TELA - self.image.get_height()))
        self.velocidade = min(2 + (dificuldade_atual * 0.3), 8) * escala_x
        if self.tipo == "fogo": self.cor_vida = (255,100,100)
        elif self.tipo == "gelo": self.cor_vida = (100,200,255)
        else: self.cor_vida = (200,150,100)
    def update(self):
        self.rect.x -= self.velocidade
        self.frame_index = (self.frame_index + self.animation_speed) % len(self.animation_frames)
        self.image = self.animation_frames[int(self.frame_index)]
    def tomar_dano(self):
        self.vida_atual -= 1; return self.vida_atual <= 0
    def draw_vida(self, surface):
        if self.vida_maxima > 1:
            barra_w, barra_h = 60 * escala_x, 8 * escala_y
            x, y = self.rect.centerx - barra_w / 2, self.rect.y - 15 * escala_y
            pygame.draw.rect(surface, (60,60,60), (x,y,barra_w,barra_h)); vida_w = int(barra_w * (self.vida_atual / self.vida_maxima))
            pygame.draw.rect(surface, self.cor_vida, (x,y,vida_w,barra_h)); pygame.draw.rect(surface, (200,200,200), (x,y,barra_w,barra_h), 1)

class Feitico(pygame.sprite.Sprite):
    def __init__(self, tipo, pos_inicio, anim_manager, mapa_comandos_voz, alvo=None):
        super().__init__()
        self.anim_manager = anim_manager
        self.tipo = tipo
        self.tipo_alvo = mapa_comandos_voz.get(tipo)
        self.animation_frames = self.anim_manager.animations[f'feitico_{self.tipo}']
        self.frame_index, self.animation_speed = 0.0, 0.3
        self.image = self.animation_frames[0]
        self.rect = self.image.get_rect(center=pos_inicio)
        self.pos = pygame.Vector2(self.rect.center)

        # Se um alvo for fornecido, persegue o alvo.
        if alvo:
            direcao = pygame.Vector2(alvo.rect.center) - self.pos
            if direcao.length() > 0:
                self.velocidade = direcao.normalize() * (15 * escala_x)
            else: # Caso raro de estar na mesma posição
                self.velocidade = pygame.Vector2(15 * escala_x, 0)
        # Se nenhum alvo for fornecido, vai reto.
        else:
            self.velocidade = pygame.Vector2(15 * escala_x, 0)

    def update(self):
        self.pos += self.velocidade; self.rect.center = self.pos
        self.frame_index = (self.frame_index + self.animation_speed) % len(self.animation_frames)
        self.image = self.animation_frames[int(self.frame_index)]
        if not tela.get_rect().colliderect(self.rect): self.kill()

class Explosao(pygame.sprite.Sprite):
    def __init__(self, position, anim_manager):
        super().__init__(); self.anim_manager = anim_manager
        self.animation_frames = self.anim_manager.animations['explosao']
        self.frame_index, self.animation_speed = 0.0, 0.3
        self.image = self.animation_frames[0]; self.rect = self.image.get_rect(center=position)
    def update(self):
        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.animation_frames): self.kill()
        else: self.image = self.animation_frames[int(self.frame_index)]

class VoiceRecognitionSystem:
    def __init__(self):
        # CORREÇÃO: Fila de comandos de voz agora é ilimitada.
        self.command_buffer = deque()
        try:
            self.recognizer = PyRecognition('pt-BR'); self.voice_available = True
            print("Sistema de reconhecimento de voz inicializado!")
        except Exception as e:
            print(f"PyRecognition falhou: {e}. Usando teclado."); self.voice_available = False
            
    def get_all_pending_transcripts(self):
        if self.voice_available:
            for speech in self.recognizer.get_all_pending(): self.command_buffer.append(speech)
        results = []; [results.append(self.command_buffer.popleft()) for _ in range(len(self.command_buffer))]
        return results
        
    def add_keyboard_command(self, command): self.command_buffer.append(command)
    
    def stop(self):
        if self.voice_available: self.recognizer.stop()

class GameState:
    def __init__(self, score_manager):
        self.score_manager = score_manager
        self.estado = "MENU"
        self.pontuacao = 0
        self.dificuldade = 0
        self.vidas = 3
        self.combo = 0
        self.player_name = ""
        self.menu_option = "INICIAR" # Pode ser INICIAR ou PONTUACOES

# --- FUNÇÕES DE LÓGICA E CONTROLE ---
# --- FUNÇÕES DE LÓGICA E CONTROLE ---
def process_voice_command(command: str):
    """
    Processa uma string de transcrição de voz e retorna uma lista de comandos canônicos identificados.
    Esta versão é mais robusta, detectando comandos como substrings dentro das palavras faladas.
    Ex: "fogos" ativa "fogo", "queimando" ativa "queimar" (que mapeia para "fogo").
    """
    if not command:
        return []

    comandos_map = {
        "fogo": ["fogo", "fire", "chama", "queimar"],
        "gelo": ["gelo", "ice", "congelar", "frio"],
        "raio": ["raio", "thunder", "trovao", "eletrico", "relampago", "rai"],
        "comecar": ["comecar", "iniciar", "start", "jogar"],
        "pontuacao": ["pontuacao", "scores", "placar"],
        "voltar": ["voltar", "menu", "retornar"],
        "parar": ["parar", "stop", "sair", "quit"]
    }

    # Cria um mapa reverso para busca eficiente: {"fogo": "fogo", "fire": "fogo", ...}
    sinonimo_map = {s: cmd for cmd, sl in comandos_map.items() for s in sl}
    # Obtém uma lista de todos os sinônimos únicos para iterar
    todos_sinonimos = list(sinonimo_map.keys())

    # Normaliza e divide a entrada de voz
    palavras_faladas = _normalize_ascii(command).split()
    comandos_identificados = []

    # Itera sobre cada palavra dita pelo jogador
    for palavra in palavras_faladas:
        # Para cada palavra, verifica se algum sinônimo corresponde como substring
        for sinonimo in todos_sinonimos:
            # A MUDANÇA PRINCIPAL:
            # Em vez de 'if palavra == sinonimo', usamos 'if sinonimo in palavra'.
            if sinonimo in palavra:
                # Adiciona o comando principal correspondente (ex: "fogo")
                comandos_identificados.append(sinonimo_map[sinonimo])
                # Encontrou uma correspondência para esta 'palavra', então
                # quebra o loop interno e vai para a próxima 'palavra' falada.
                # Isso evita adicionar o mesmo comando duas vezes para uma única palavra (ex: "fogofogo").
                break
    
    return comandos_identificados

def reset_game_state(game_state, all_groups):
    print(f"--- INICIANDO JOGO PARA: {game_state.player_name} ---")
    game_state.pontuacao, game_state.dificuldade, game_state.vidas, game_state.combo = 0, 0, 3, 0
    for group in all_groups.values():
        if isinstance(group, pygame.sprite.Group): group.empty()
    all_groups['todos'].add(all_groups['mago_sprite'])
    global cenario_x; cenario_x = 0

def draw_text_centered(surface, text, font, color, y_pos):
    rendered_text = font.render(text, True, color)
    rect = rendered_text.get_rect(center=(LARGURA_TELA / 2, y_pos))
    surface.blit(rendered_text, rect)

def draw_ui(surface, game_state, voice_available):
    if game_state.estado == "JOGANDO":
        surface.blit(fonte.render(f"Pontos: {game_state.pontuacao}", True, (255, 255, 255)), (20, 20))
        for i in range(game_state.vidas): pygame.draw.circle(surface, (255, 100, 100), (40 + i * 40, 80), 15, 0)
        if game_state.combo > 1: surface.blit(fonte_media.render(f"Combo x{game_state.combo}!", True, (255, 215, 0)), (20, 120))
    elif game_state.estado == "MENU":
        draw_text_centered(surface, "MAGO DOS COMANDOS", fonte, (255, 255, 100), ALTURA_TELA / 4)
        
        cor_iniciar = (255, 255, 0) if game_state.menu_option == "INICIAR" else (200, 255, 200)
        cor_pontos = (255, 255, 0) if game_state.menu_option == "PONTUACOES" else (200, 255, 200)

        draw_text_centered(surface, "Iniciar Jogo", fonte_media, cor_iniciar, ALTURA_TELA / 2)
        draw_text_centered(surface, "Pontuações", fonte_media, cor_pontos, ALTURA_TELA / 2 + 60)
        
        instrucao = "Use SETAS e ENTER ou fale 'COMEÇAR'/'PONTUAÇÃO'" if voice_available else "Use SETAS e ENTER"
        draw_text_centered(surface, instrucao, fonte_pequena, (200, 200, 200), ALTURA_TELA * 0.75)

    elif game_state.estado == "SCORES":
        draw_text_centered(surface, "MELHORES PONTUAÇÕES", fonte, (255, 215, 0), ALTURA_TELA / 6)
        top_scores = game_state.score_manager.get_top_scores(5)
        if not top_scores:
            draw_text_centered(surface, "Nenhuma pontuação registrada ainda.", fonte_pequena, (255, 255, 255), ALTURA_TELA / 2)
        else:
            for i, score_entry in enumerate(top_scores):
                texto = f"{i+1}. {score_entry['name']}: {score_entry['score']}"
                draw_text_centered(surface, texto, fonte_media, (255, 255, 255), ALTURA_TELA / 3 + i * 60)
        instrucao = "Fale 'VOLTAR' ou pressione ESC para retornar ao menu."
        draw_text_centered(surface, instrucao, fonte_pequena, (200, 200, 200), ALTURA_TELA * 0.85)

    elif game_state.estado == "GET_NAME":
        draw_text_centered(surface, "DIGITE SEU NOME", fonte, (255, 255, 100), ALTURA_TELA / 3)
        nome_render = fonte_media.render(game_state.player_name, True, (255, 255, 255))
        nome_rect = nome_render.get_rect(center=(LARGURA_TELA/2, ALTURA_TELA/2))
        pygame.draw.rect(tela, (30, 30, 30), (nome_rect.x - 10, nome_rect.y - 10, nome_rect.width + 20, nome_rect.height + 20))
        tela.blit(nome_render, nome_rect)
        instrucao = "Pressione ENTER ou fale 'COMEÇAR' para continuar"
        draw_text_centered(surface, instrucao, fonte_pequena, (200, 255, 200), ALTURA_TELA * 0.65)

    elif game_state.estado == "GAME_OVER":
        draw_text_centered(surface, "GAME OVER", fonte, (255, 50, 50), ALTURA_TELA / 2 - 50)
        draw_text_centered(surface, f"Pontuação final: {game_state.pontuacao}", fonte_media, (255, 255, 255), ALTURA_TELA / 2 + 20)
        draw_text_centered(surface, "Voltando para o menu...", fonte_pequena, (200, 200, 200), ALTURA_TELA * 0.8)

# --- FUNÇÃO PARA DESENHAR O CENÁRIO ---
def draw_scrolling_background():
    global cenario_x
    # Desenha a primeira imagem
    tela.blit(cenario_img, (cenario_x, 0))
    # Desenha a segunda imagem logo após a primeira
    tela.blit(cenario_img, (cenario_x + LARGURA_TELA, 0))
    # Se a primeira imagem saiu completamente da tela, reseta a posição
    if cenario_x <= -LARGURA_TELA:
        cenario_x = 0

def menu_loop(game_state, voice_system):
    global cenario_x
    looping = True
    while looping:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "QUIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: return "QUIT"
                if event.key == pygame.K_DOWN:
                    game_state.menu_option = "PONTUACOES"
                if event.key == pygame.K_UP:
                    game_state.menu_option = "INICIAR"
                if event.key == pygame.K_RETURN:
                    if game_state.menu_option == "INICIAR":
                        game_state.estado = "GET_NAME"
                    else:
                        game_state.estado = "SCORES"
                    looping = False
        
        transcricoes = voice_system.get_all_pending_transcripts()
        for trans in transcricoes:
            comandos = process_voice_command(trans)
            if "comecar" in comandos:
                game_state.estado = "GET_NAME"; looping = False
            elif "pontuacao" in comandos:
                game_state.estado = "SCORES"; looping = False

        cenario_x -= 0.2 * escala_x
        draw_scrolling_background()
        draw_ui(tela, game_state, voice_system.voice_available)
        pygame.display.flip(); clock.tick(FPS)

def scores_loop(game_state, voice_system):
    global cenario_x
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "QUIT"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state.estado = "MENU"; return
        
        transcricoes = voice_system.get_all_pending_transcripts()
        if any("voltar" in process_voice_command(t) for t in transcricoes):
            game_state.estado = "MENU"; return

        cenario_x -= 0.2 * escala_x
        draw_scrolling_background()
        draw_ui(tela, game_state, voice_system.voice_available)
        pygame.display.flip(); clock.tick(FPS)

def get_name_loop(game_state, voice_system):
    global cenario_x
    game_state.player_name = ""
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "QUIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state.estado = "MENU"; return
                if event.key == pygame.K_RETURN and game_state.player_name:
                    game_state.estado = "JOGANDO"; return
                if event.key == pygame.K_BACKSPACE:
                    game_state.player_name = game_state.player_name[:-1]
                else:
                    if len(game_state.player_name) < 15 and event.unicode.isalnum():
                        game_state.player_name += event.unicode
        
        transcricoes = voice_system.get_all_pending_transcripts()
        if any("comecar" in process_voice_command(t) for t in transcricoes) and game_state.player_name:
            game_state.estado = "JOGANDO"; return

        cenario_x -= 0.2 * escala_x
        draw_scrolling_background()
        draw_ui(tela, game_state, voice_system.voice_available)
        pygame.display.flip(); clock.tick(FPS)

def game_over_loop(game_state):
    game_state.score_manager.save_score(game_state.player_name, game_state.pontuacao)
    start_time = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start_time < 3000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "QUIT"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return "QUIT"
        
        tela.fill((0,0,0))
        draw_ui(tela, game_state, False)
        pygame.display.flip()
        clock.tick(15)
    
    game_state.estado = "MENU"
    return "MENU"

def game_loop(game_state, voice_system, anim_manager):
    global cenario_x
    mago = Mago(anim_manager)
    all_groups = {'todos': pygame.sprite.Group(), 'mago_sprite': mago, 'monstros': pygame.sprite.Group(), 'feiticos': pygame.sprite.Group(), 'aprendizes': pygame.sprite.Group(), 'explosoes': pygame.sprite.Group()}
    reset_game_state(game_state, all_groups)
    
    aprendiz_ativo, PONTUACAO_PARA_APRENDIZ = None, 250
    mapa_comandos_voz = {"gelo": "fogo", "fogo": "gelo", "raio": "terra"}
    intervalo_spawn, ultimo_spawn = 2000, pygame.time.get_ticks()

    fila_de_comandos_de_voz = deque()

    while game_state.estado == "JOGANDO":
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                game_state.estado = "QUIT"; break
            
            if not voice_system.voice_available and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: fila_de_comandos_de_voz.append("fogo")
                if event.key == pygame.K_2: fila_de_comandos_de_voz.append("gelo")
                if event.key == pygame.K_3: fila_de_comandos_de_voz.append("raio")
        
        transcricoes = voice_system.get_all_pending_transcripts()
        for trans in transcricoes:
            comandos = process_voice_command(trans)
            for cmd in comandos:
                if cmd in mapa_comandos_voz:
                    fila_de_comandos_de_voz.append(cmd)
                    
        # Lança um feitiço por frame, enquanto houver comandos na fila.
        if fila_de_comandos_de_voz:
            tipo_feitico = fila_de_comandos_de_voz.popleft()
            
            mago.cast_spell()

            tipo_alvo = mapa_comandos_voz.get(tipo_feitico)
            alvos = [m for m in all_groups['monstros'] if m.tipo == tipo_alvo]
            
            alvo_final = None
            if alvos:
                # Mira no alvo mais próximo
                alvo_final = min(alvos, key=lambda m: m.rect.x)
                
            # Cria UM feitiço, com ou sem alvo
            feitico_novo = Feitico(tipo_feitico, mago.rect.center, anim_manager, mapa_comandos_voz, alvo=alvo_final)
            all_groups['todos'].add(feitico_novo)
            all_groups['feiticos'].add(feitico_novo)
        
        cenario_x -= 0.5 * escala_x
        if not aprendiz_ativo and game_state.pontuacao >= PONTUACAO_PARA_APRENDIZ:
            aprendiz_ativo=Aprendiz(mago,anim_manager,mapa_comandos_voz); all_groups['todos'].add(aprendiz_ativo); all_groups['aprendizes'].add(aprendiz_ativo)
        if aprendiz_ativo: aprendiz_ativo.logica_de_combate(mago,all_groups['monstros'],all_groups['todos'],all_groups['feiticos'])
        if pygame.time.get_ticks() - ultimo_spawn > intervalo_spawn:
            monstro = Monstro(game_state.dificuldade, anim_manager)
            all_groups['todos'].add(monstro); all_groups['monstros'].add(monstro); ultimo_spawn = pygame.time.get_ticks()
        
        all_groups['todos'].update(); all_groups['explosoes'].update()
        
        hits = pygame.sprite.groupcollide(all_groups['monstros'], all_groups['feiticos'], False, True)
        for monstro, feiticos_hit in hits.items():
            if feiticos_hit[0].tipo_alvo == monstro.tipo:
                for _ in feiticos_hit:
                    if monstro.tomar_dano():
                        game_state.pontuacao += 10 + game_state.combo * 2; game_state.combo += 1
                        all_groups['explosoes'].add(Explosao(monstro.rect.center, anim_manager)); monstro.kill()
                        break
            else: game_state.combo = 0
        
        nova_dif = game_state.pontuacao // 100
        if nova_dif > game_state.dificuldade: game_state.dificuldade = nova_dif; intervalo_spawn = max(500, 2000 - game_state.dificuldade*150)
        for monstro in list(all_groups['monstros']):
            if monstro.rect.right < 0:
                monstro.kill(); game_state.vidas -= 1; game_state.combo = 0
                if game_state.vidas <= 0:
                    game_state.estado = "GAME_OVER"
        
        draw_scrolling_background()
        all_groups['todos'].draw(tela); all_groups['explosoes'].draw(tela)
        for m in all_groups['monstros']: m.draw_vida(tela)
        draw_ui(tela, game_state, voice_system.voice_available)
        
        pygame.display.flip()
        clock.tick(FPS)

# --- FUNÇÃO PRINCIPAL ---
def main():
    voice_system = VoiceRecognitionSystem()
    score_manager = ScoreManager()
    game_state = GameState(score_manager)
    anim_manager = AnimationManager()
    
    # Carregamento único no início do jogo
    anim_manager.load_animation_from_folder('mago_idle', pasta_mago_anim, (100, 120))
    anim_manager.load_animation_from_folder('mago_cast', pasta_mago_anim, (110, 120))
    anim_manager.load_animation_from_folder('monstro_fogo', pasta_monstro_fogo_anim, (80, 80))
    anim_manager.load_animation_from_folder('monstro_gelo', pasta_monstro_gelo_anim, (80, 80))
    anim_manager.load_animation_from_folder('monstro_terra', pasta_monstro_terra_anim, (80, 80))
    anim_manager.load_animation_from_folder('feitico_fogo', pasta_feitico_fogo_anim, (50, 50))
    anim_manager.load_animation_from_folder('feitico_gelo', pasta_feitico_gelo_anim, (50, 50))
    anim_manager.load_animation_from_folder('feitico_raio', pasta_feitico_raio_anim, (50, 50))
    anim_manager.load_animation_from_folder('explosao', pasta_explosao_anim, (100, 100))
    anim_manager.load_animation_from_folder('aprendiz_idle', pasta_aprendiz_anim, (70, 90))

    running = True
    while running:
        if game_state.estado == "MENU":
            if menu_loop(game_state, voice_system) == "QUIT":
                running = False
        
        elif game_state.estado == "SCORES":
            if scores_loop(game_state, voice_system) == "QUIT":
                running = False

        elif game_state.estado == "GET_NAME":
            if get_name_loop(game_state, voice_system) == "QUIT":
                running = False
        
        elif game_state.estado == "JOGANDO":
            game_loop(game_state, voice_system, anim_manager)
        
        elif game_state.estado == "GAME_OVER":
            if game_over_loop(game_state) == "QUIT":
                running = False
        
        elif game_state.estado == "QUIT":
            running = False

    voice_system.stop()
    pygame.quit()

if __name__ == '__main__':
    main()