import os

# 1. 모으고 싶은 확장자 설정 (필요한 것만 골라 담기)
extensions = ['.py', '.ts', '.tsx', '.css','.json']

# 2. 제외할 폴더나 파일 설정 (안티그라비티!)
exclude_dirs = [
    'node_modules', '.git', '__pycache__', '.venv', 
    'dist', 'build', '.vscode', 'venv', '.idea', 'migrations','.env','./.env','readme.md','README.md'
]
output_file = 'project_full_summary.txt'

def gather_code():
    print(f"🚀 코드를 모으기 시작합니다: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 프로젝트 전체를 돌며 탐색
        for root, dirs, files in os.walk('.'):
            
            # 제외할 폴더는 건너뛰기
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # 설정한 확장자만 포함
                if any(file.endswith(ext) for ext in extensions):
                    # 자기 자신(스크립트)과 결과 파일은 제외
                    if file in [os.path.basename(__file__), output_file]:
                        continue
                        
                    file_path = os.path.join(root, file)
                    
                    # 파일 헤더 작성 (구분선)
                    f.write(f"\n\n{'='*50}\n")
                    f.write(f"FILE: {file_path}\n")
                    f.write(f"{'='*50}\n\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as code_f:
                            f.write(code_f.read())
                    except Exception as e:
                        f.write(f"[파일 읽기 실패] {str(e)}")
                        
    print(f"✅ 모든 코드가 {output_file}에 저장되었습니다!")

if __name__ == "__main__":
    gather_code()