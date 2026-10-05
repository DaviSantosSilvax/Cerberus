import os
import glob
import re
import pickle
import numpy as np
import cv2
import insightface
from insightface.app import FaceAnalysis

class SistemaReconhecimentoFacial:
    def __init__(self, pasta_fotos="Bd_Fotos", modelo_nome="buffalo_l", threshold_similitude=0.40):
        """
        Inicializa o sistema de reconhecimento facial utilizando a biblioteca InsightFace.
        
        :param pasta_fotos: Diretório contendo as fotos das pessoas (ex: 'davi_1.jpg', 'davi_2.jpg')
        :param modelo_nome: Nome do pacote de modelos InsightFace (padrão: 'buffalo_l')
        :param threshold_similitude: Limiar de similaridade de cosseno para reconhecer a pessoa (padrão: 0.40)
        """
        self.pasta_fotos = pasta_fotos
        self.threshold = threshold_similitude
        self.banco_embeddings = {} # {'Davi': [emb1, emb2], 'Maria': [emb1]}
        self.banco_medias = {}     # {'Davi': emb_medio, 'Maria': emb_medio}
        self.cache_file = os.path.join(pasta_fotos, ".embeddings_cache.pkl")
        
        print(f"[InsightFace] Carregando modelos de visão ({modelo_nome})...")
        # Utiliza CPU Execution Provider para maior portabilidade
        self.app = FaceAnalysis(name=modelo_nome, providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        print("[InsightFace] Modelos carregados com sucesso!")
        
        # Indexa as fotos cadastradas no banco de fotos
        self.carregar_banco_de_faces()

    def _extrair_nome_do_arquivo(self, nome_arquivo: str) -> str:
        """
        Extrai o nome da pessoa baseado na convenção: nome_da_pessoa_(numero)
        Exemplos:
        - davi_1.jpg -> Davi
        - davi_2.png -> Davi
        - davi_souza_03.jpeg -> Davi Souza
        """
        nome_sem_ext = os.path.splitext(nome_arquivo)[0]
        # Remove o sufixo numerico final como _1, _02, _3 se presente
        nome_limpo = re.sub(r'_\d+$', '', nome_sem_ext)
        # Converte underscores em espacos e aplica Capitalização
        nome_formatado = nome_limpo.replace('_', ' ').strip().title()
        return nome_formatado

    def carregar_banco_de_faces(self, forcar_reindexacao=False):
        """
        Varre a pasta de fotos, detecta as faces com InsightFace e armazena os embeddings.
        Utiliza cache local inteligente que reindexa automaticamente se novas fotos forem adicionadas.
        """
        if not os.path.exists(self.pasta_fotos):
            os.makedirs(self.pasta_fotos, exist_ok=True)
            print(f"[AVISO] Pasta '{self.pasta_fotos}' criada. Coloque as fotos no formato nome_(numero).jpg nela.")
            return

        extensoes = ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.webp')
        arquivos = []
        for ext in extensoes:
            arquivos.extend(glob.glob(os.path.join(self.pasta_fotos, ext)))
            arquivos.extend(glob.glob(os.path.join(self.pasta_fotos, ext.upper())))

        arquivos_basenames = sorted([os.path.basename(f) for f in arquivos if not os.path.basename(f).startswith('.')])

        # Tenta carregar do cache salvo em disco se disponível e se os arquivos não mudaram
        if not forcar_reindexacao and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    data = pickle.load(f)
                    cached_arquivos = sorted(data.get('arquivos', []))
                    if cached_arquivos == arquivos_basenames:
                        self.banco_embeddings = data.get('embeddings', {})
                        self.banco_medias = data.get('medias', {})
                        print(f"[Cache] Pessoas carregadas do cache: {list(self.banco_medias.keys())}")
                        return
                    else:
                        print(f"[Cache] Novas fotos detectadas em '{self.pasta_fotos}'! Atualizando índice...")
            except Exception as e:
                print(f"[Cache] Erro ao carregar cache ({e}). Reindexando fotos...")

        print(f"[Indexador] Processando fotos da pasta '{self.pasta_fotos}'...")

        if not arquivos:
            print(f"[AVISO] Nenhuma foto encontrada na pasta '{self.pasta_fotos}'.")
            return

        self.banco_embeddings = {}
        contagem_fotos = 0

        for caminho_img in arquivos:
            nome_arquivo = os.path.basename(caminho_img)
            # Ignora arquivo de cache se estiver na pasta
            if nome_arquivo.startswith('.'):
                continue

            nome_pessoa = self._extrair_nome_do_arquivo(nome_arquivo)

            img = cv2.imread(caminho_img)
            if img is None:
                print(f"  [x] Erro ao ler imagem: {nome_arquivo}")
                continue

            faces = self.app.get(img)
            if not faces:
                print(f"  [x] Nenhuma face encontrada em: {nome_arquivo}")
                continue

            # Pega o embedding da face principal da foto de cadastro
            embedding = faces[0].normed_embedding

            if nome_pessoa not in self.banco_embeddings:
                self.banco_embeddings[nome_pessoa] = []
            self.banco_embeddings[nome_pessoa].append(embedding)
            contagem_fotos += 1
            print(f"  [v] Face cadastrada: '{nome_pessoa}' (arquivo: {nome_arquivo})")

        # Calcula o embedding medio para cada pessoa (vetor medio normalizado)
        self.banco_medias = {}
        for pessoa, embs in self.banco_embeddings.items():
            emb_medio = np.mean(embs, axis=0)
            emb_medio = emb_medio / np.linalg.norm(emb_medio)
            self.banco_medias[pessoa] = emb_medio

        # Salva em cache para rápido carregamento posterior
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump({'embeddings': self.banco_embeddings, 'medias': self.banco_medias, 'arquivos': arquivos_basenames}, f)
            print(f"[Cache] Embeddings salvos em '{self.cache_file}'.")
        except Exception as e:
            print(f"[Cache] Erro ao gravar cache: {e}")

        print(f"[Sucesso] {contagem_fotos} foto(s) cadastradas para {len(self.banco_medias)} pessoa(s): {list(self.banco_medias.keys())}")

    def identificar_faces(self, imagem_input):
        """
        Recebe um caminho de imagem ou ndarray (OpenCV) e retorna uma lista
        com todas as faces identificadas e seus respectivos nomes.
        Utiliza Max-Pooling contra todas as fotos cadastradas de cada pessoa.
        """
        if isinstance(imagem_input, str):
            img = cv2.imread(imagem_input)
            if img is None:
                raise ValueError(f"Não foi possível carregar a imagem do caminho: {imagem_input}")
        else:
            img = imagem_input

        faces_detectadas = self.app.get(img)
        resultados = []

        if not self.banco_embeddings:
            for face in faces_detectadas:
                bbox = face.bbox.astype(int).tolist()
                resultados.append({
                    "nome": "Desconhecido",
                    "similaridade": 0.0,
                    "bbox": bbox,
                    "gender": getattr(face, 'gender', None),
                    "age": getattr(face, 'age', None)
                })
            return resultados

        for face in faces_detectadas:
            target_emb = face.normed_embedding
            
            melhor_score = -1.0
            melhor_pessoa = "Desconhecido"

            for pessoa, embs in self.banco_embeddings.items():
                if not embs:
                    continue
                matriz_embs = np.vstack(embs)
                sims = np.dot(matriz_embs, target_emb)
                # Max-pooling: similaridade com a melhor foto cadastrada da pessoa
                score = float(np.max(sims))
                if score > melhor_score:
                    melhor_score = score
                    melhor_pessoa = pessoa

            if melhor_score >= self.threshold:
                nome_identificado = melhor_pessoa
            else:
                nome_identificado = "Desconhecido"

            bbox = face.bbox.astype(int).tolist() # [x1, y1, x2, y2]
            resultados.append({
                "nome": nome_identificado,
                "similaridade": round(melhor_score, 4),
                "bbox": bbox,
                "gender": getattr(face, 'gender', None),
                "age": getattr(face, 'age', None)
            })

        return resultados

    def obter_nome_pessoa_principal(self, imagem_input) -> str:
        """
        Retorna apenas o NOME da pessoa com a maior face na imagem (ou 'Desconhecido' / 'Ninguém').
        Util para a IA conversar chamando a pessoa pelo nome!
        """
        resultados = self.identificar_faces(imagem_input)
        if not resultados:
            return "Ninguém"
        
        # Ordena pela area da caixa delimitadora (face mais proxima da camera)
        resultados.sort(key=lambda r: (r['bbox'][2] - r['bbox'][0]) * (r['bbox'][3] - r['bbox'][1]), reverse=True)
        return resultados[0]['nome']

    def testar_em_webcam(self, camera_id=0):
        """
        Abre a webcam local para teste visual de reconhecimento em tempo real.
        """
        print(f"[Webcam] Iniciando câmera {camera_id}... Pressione 'q' na janela para encerrar.")
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            print("[ERRO] Não foi possível acessar a webcam.")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            resultados = self.identificar_faces(frame)

            for res in resultados:
                x1, y1, x2, y2 = res['bbox']
                nome = res['nome']
                sim = res['similaridade']

                cor = (0, 255, 0) if nome != "Desconhecido" else (0, 0, 255)
                label = f"{nome} ({sim:.2f})" if nome != "Desconhecido" else "Desconhecido"

                cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
                cv2.putText(frame, label, (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)

            cv2.imshow("Cerberus - Reconhecimento Facial (InsightFace)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
