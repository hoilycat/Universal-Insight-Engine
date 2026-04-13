import cv2
import numpy as np
from rembg import remove
import easyocr


# 1. OCR 리더기 초기화 (영어와 한국어 지원)
# gpu=True로 설정하면 그래픽카드를 써서 훨씬 빨라짐
reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False) 

def analyze_text_with_ocr(image_bytes):
    """이미지 내 텍스트 내용, 위치, 폰트 스타일 추정"""
    # bytes를 OpenCV 이미지로 변환
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 2. OCR 실행
    # 결과값 형식: [[(좌표), "텍스트", 확률], ...]
    results = reader.readtext(img)
    
    if not results:
        return {"has_text": False, "text_content": "", "text_area_ratio": 0.0, "raw_results": []}

    full_text = []
    total_text_area = 0
    img_area = img.shape[0] * img.shape[1]

    for (bbox, text, prob) in results:
        if prob > 0.5: # 신뢰도가 50% 이상인 것만 취급
            full_text.append(text)
            # 사각형 면적 계산 (bbox는 [[x1,y1], [x2,y1], [x2,y2], [x1,y2]] 형태)
            width = bbox[1][0] - bbox[0][0]
            height = bbox[2][1] - bbox[1][1]
            total_text_area += (width * height)

    return {
        "has_text": len(full_text) > 0,
        "text_content": " / ".join(full_text),
        "text_count": len(full_text),
        "text_area_ratio": round((total_text_area / img_area) * 100, 2),
        "raw_results": results
    }
    
    
def get_graphics_only_image(image_bytes, ocr_results):
    """글자를 지워버린 순수 그래픽 이미지를 반환 (복잡도 분석용)"""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 글자가 있는 곳을 하얀색으로 칠해버림 (Inpainting 기법)
    for (bbox, text, prob) in ocr_results:
        top_left = tuple(map(int, bbox[0]))
        bottom_right = tuple(map(int, bbox[2]))
        # 글자 부분을 배경색(또는 흰색)으로 덮어서 엣지 검출을 방해하지 않게 함
        cv2.rectangle(img, top_left, bottom_right, (255, 255, 255), -1)
    
    # 처리된 이미지를 다시 bytes로 변환
    _, encoded_img = cv2.imencode('.jpg', img)
    return encoded_img.tobytes()


def get_image_and_mode(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    if img is None: return None, None
    # 4채널(BGRA)이면 로고 모드로 판단
    is_logo_mode = (len(img.shape) == 3 and img.shape[2] == 4)
    return img, is_logo_mode

def calculate_brightness(image_bytes):
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0

    bgr_img = img[:, :, :3] if is_logo_mode else img

    if is_logo_mode:
        # 투명하지 않은 모든 픽셀을 대상으로 함 (검정색 글자도 브랜드의 일부!)
        mask = img[:, :, 3] > 0
        pixels = bgr_img[mask]
    else:
        pixels = bgr_img.reshape(-1, 3)

    if len(pixels) == 0: return 0.0

    # 지각적 밝기 공식 (Luminance)
    # 변수가 흐릿해지는 걸 막기 위해 필요한 것만 슬라이싱해서 씁니다.
    b_p = pixels[:, 0]
    g_p = pixels[:, 1]
    r_p = pixels[:, 2]
    luma = 0.299 * r_p + 0.587 * g_p + 0.114 * b_p
    
    return float(np.mean(luma))



def calculate_saturation_ratio(image_bytes):
    """이미지의 평균 채도 추출 (0~100)"""
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    hsv = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2HSV)
    s_channel = hsv[:, :, 1]
    if is_logo_mode:
        mask = img[:, :, 3] > 0
        pixels = s_channel[mask]
    else:
        pixels = s_channel.flatten()
    return float((np.mean(pixels) / 255) * 100) if len(pixels) > 0 else 0.0


def calculate_complexity(image_bytes):
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    # 로고면 BGRA, 일반이면 BGR을 Gray로 변환
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if is_logo_mode else cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 150, 250)
    
    if is_logo_mode:
        mask = img[:, :, 3] > 0
        area = np.count_nonzero(mask)
        # 내용물 영역 안에서만 엣지 밀도 계산
        score = (np.count_nonzero(edges & mask) / area) * 400 if area > 0 else 0.0
    else:
        score = (np.count_nonzero(edges) / edges.size) * 300
        
    return min(float(score), 100.0)


#여백 비율 로직
def calculate_space_ratio(image_bytes):
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0

    # 1. 로고 모드(투명 배경)일 때는 기존처럼 투명도 기준
    if is_logo_mode:
        return float((np.count_nonzero(img[:, :, 3] == 0) / (img.shape[0] * img.shape[1])) * 100)
    
    # 2. 일반 이미지(포스터 등)일 때: "지능형 음의 공간(Negative Space)" 계산
    # 그레이스케일 변환
    gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    
    # 가우시안 블러로 미세한 노이즈 제거 (배경의 질감을 뭉개줌)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 엣지 검출 (Canny)
    edges = cv2.Canny(blurred, 50, 150)
    
    # 엣지 팽창 (글자나 캐릭터 주변의 아주 가까운 공간도 '내용물'로 취급하기 위해)
    kernel = np.ones((5, 5), np.uint8)
    dilated_edges = cv2.dilate(edges, kernel, iterations=2)
    
    # 전체 면적 중 엣지가 없는(0인) 영역의 비율 계산
    # 즉, 아무런 선이나 디테일이 없는 '평평한 면'을 여백으로 봄
    non_edge_pixels = np.count_nonzero(dilated_edges == 0)
    total_pixels = gray.size
    
    space_ratio = (non_edge_pixels / total_pixels) * 100
    
    # 너무 뻥튀기 되지 않게 보정 (보통 포스터에서 아무것도 없는 면이 80%를 넘기 힘듦)
    return min(float(space_ratio), 100.0)


def calculate_symmetry(image_bytes):
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    h, w = img.shape[:2]
    half = w // 2
    left, right = img[:, :half], cv2.flip(img[:, w - half:], 1)
    
    if is_logo_mode:
        score = 100 - (np.mean(cv2.absdiff(left, right)) / 255 * 200)
    else:
        score = 100 - (abs(np.mean(left) - np.mean(right)) / 255 * 500)
    return max(float(score), 0.0)


def calculate_saliency(image_bytes):
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
    success, map_data = saliency.computeSaliency(img[:, :, :3] if is_logo_mode else img)
    return min(float(np.mean(map_data) * 500), 100.0) if success else 0.0



def extract_color_dna(image_bytes, k=10, remove_bg_internally=False): 
    target_bytes = image_bytes
    
    # 1. 내부적으로 배경 제거가 필요하다면 실행
    if remove_bg_internally:
        from rembg import remove
        target_bytes = remove(image_bytes)

    # 2. 이미지 로드 및 모드 판별 (여기서 한 번만 수행)
    img, is_logo_mode = get_image_and_mode(target_bytes)
    if img is None: return []
    
    # 3. 분석용 픽셀 추출
    # 로고 모드면 투명하지 않은 것만, 아니면 전체 픽셀
    pixels = img[img[:, :, 3] > 0][:, :3] if is_logo_mode else img.reshape((-1, 3))
    
    if len(pixels) < k: return []
    
    # 4. K-means 알고리즘 실행
    data = np.float32(pixels)
    _, labels, centers = cv2.kmeans(data, k, None, (cv2.TERM_CRITERIA_EPS + 10, 10, 1.0), 10, cv2.KMEANS_RANDOM_CENTERS)
    
    counts = np.bincount(labels.flatten())
    total = len(pixels)
    
    candidates = []
    for i in range(len(centers)):
        rgb = centers[i][::-1] # BGR -> RGB 변환
        percentage = counts[i] / total
        
        if percentage < 0.005: continue # 너무 작은 영역(노이즈) 제외
        
        candidates.append({
            'rgb': rgb,
            'hex': f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}",
            'score': percentage
        })
    
    # 5. 면적 순으로 정렬
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # 6. 너무 비슷한 색상끼리는 합치거나 제외하는 필터링
    final = []
    for c in candidates:
        if len(final) >= 5: break # 최종 5개만 선택
        
        # 💡 필터 기준을 30 -> 20으로 낮춰서 핑크색이 다른 색과 비슷해도 살아남게 함
        if not any(np.linalg.norm(np.array(c['rgb']) - np.array(f['rgb'])) < 20 for f in final):
            final.append(c)
            
    return [c['hex'] for c in final]



def calculate_contrast(image_bytes):
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2GRAY)
    
    if is_logo_mode:
        mask = img[:, :, 3] > 0
        contrast = gray[mask].std() if np.count_nonzero(mask) > 0 else 0.0
    else:
        contrast = gray.std()
        
    return min(float(contrast * 0.8), 100.0)

def calculate_composition(image_bytes):
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
    success, map_data = saliency.computeSaliency(img[:, :, :3] if is_logo_mode else img)
    if not success: return 0.0

    M = cv2.moments((map_data * 255).astype(np.uint8))
    if M["m00"] == 0: return 0.0
    cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
    
    h, w = map_data.shape
    points = [(w/3, h/3), (2/3*w, h/3), (w/3, 2/3*h), (2/3*w, 2/3*h)]
    min_dist = min([((cx-px)**2 + (cy-py)**2)**0.5 for px, py in points])
    
    return float(100 - (min_dist / ((w**2 + h**2)**0.5 / 2) * 100))

def calculate_aspect_ratio(image_bytes):
    img, _ = get_image_and_mode(image_bytes)
    if img is None: return 1.0
    h, w = img.shape[:2]
    return round(w / h, 2)

def calculate_effective_color_count(image_bytes, threshold=0.01):
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0
    pixels = img[img[:, :, 3] > 0][:, :3] if is_logo_mode else img.reshape((-1, 3))
    if len(pixels) < 100: return 0
    
    data = np.float32(pixels)
    _, labels, _ = cv2.kmeans(data, 12, None, (cv2.TERM_CRITERIA_EPS + 10, 10, 1.0), 10, cv2.KMEANS_RANDOM_CENTERS)
    counts = np.bincount(labels.flatten())
    total = len(pixels)
    return len([c for c in counts if c / total > threshold])

def calculate_typography_ratio(image_bytes):
    img, _ = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    text_area = 0
    for cnt in contours:
        _, _, w, h = cv2.boundingRect(cnt)
        if 1.5 < (w/h) < 20: text_area += cv2.contourArea(cnt)
    return min(float((text_area / (img.shape[0] * img.shape[1])) * 500), 100.0)


def calculate_color_harmony_score(image_bytes):
    img, _ = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    hsv = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2HSV)
    h_pixels = hsv[:,:,0].flatten()
    if len(h_pixels) == 0: return 0.0
    return max(0.0, 100 - (np.std(h_pixels) / 90 * 100))

#채도
def calculate_average_saturation(image_bytes):
    """이미지의 평균 채도 추출 (0~100)"""
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    
    hsv = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2HSV)
    s_channel = hsv[:, :, 1] # S(Saturation) 채널만 추출

    if is_logo_mode:
        mask = img[:, :, 3] > 0
        pixels = s_channel[mask]
    else:
        pixels = s_channel.flatten()

    # 0~255 범위를 0~100으로 정규화
    return float((np.mean(pixels) / 255) * 100) if len(pixels) > 0 else 0.0


def calculate_roundness(image_bytes):
    """디자인의 원형도/곡률 분석 (0~100)"""
    img, is_logo_mode = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    
    # 1. 전처리 (그레이스케일 및 이진화)
    gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    # 2. 윤곽선 찾기
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return 0.0
    
    # 가장 큰 덩어리(메인 심볼) 기준
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)
    
    if perimeter == 0: return 0.0
    
    # 3. 원형도 공식: 4 * pi * (면적 / 둘레의 제곱)
    # 원에 가까울수록 1.0, 복잡하거나 길쭉할수록 0에 가까움
    circularity = (4 * np.pi * area) / (perimeter ** 2)
    return min(float(circularity * 100), 100.0)


def calculate_straightness(image_bytes):
    """직선 비중 분석 (Hough Lines 활용, 0~100)"""
    img, _ = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    
    
    # 이미지를 흑백으로 처리함. 컴퓨터는 색깔보다 밝기 차이를 더 잘 봄
    gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2GRAY)
    
    # 전처리: 가우시안 블러로 저해상도 노이즈(계단 현상)를 부드럽게 뭉개주기
    blurred = cv2.GaussianBlur(gray, (5, 5), 0) # 이 한 줄이 '안경' 역할을 함.

    # 엣지 검출 (블러 처리된 이미지로)
    edges = cv2.Canny(blurred, 50, 150)

    # 이미지 크기에 비례해서 최소 직선 길이(threshold)를 동적으로 설정
    h, w = img.shape[:2]
    dynamic_min_length = int(min(w, h) * 0.1) # 이미지 짧은 쪽의 10% 길이

    # 직선 검출 실행 (최소 30픽셀은 넘어야 선으로 인정)
    lines = cv2.HoughLinesP(
        edges, 
        1, 
        np.pi/180, 
        threshold=50, 
        minLineLength=max(30, dynamic_min_length), 
        maxLineGap=10
    )
   

    if lines is None: return 0.0

    #단순 개수가 아니라 '직선의 총 길이'로 점수를 매기면 훨씬 정확함
    total_line_length = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        total_line_length += length
        
    # 이미지 크기 대비 직선의 비중으로 점수화 
    score = (total_line_length / (img.shape[0] + img.shape[1])) * 10
    return min(float(score), 100.0)


def calculate_smoothness(image_bytes):
    """표면의 매끄러움 분석 (질감/노이즈 판별, 0~100)"""
    img, _ = get_image_and_mode(image_bytes)
    if img is None: return 0.0
    
    # 1. 라플라시안 분산(Laplacian Variance)을 이용한 텍스처 측정
    gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # 2. 분산이 낮을수록 매끄러운(Flat) 디자인, 높을수록 거친(Texture) 디자인
    # 평평한 색면 위주의 로고는 보통 분산이 낮음
    score = 100 - min(float(variance / 20), 100.0)
    return score