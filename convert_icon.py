from PIL import Image
import os

def convert_jpg_to_ico(jpg_path, ico_path):
    """将JPG图片转换为ICO格式"""
    try:
        # 打开JPG图片
        img = Image.open(jpg_path)
        
        # 转换为RGBA模式（支持透明度）
        img = img.convert("RGBA")
        
        # 保存为ICO格式
        img.save(ico_path, format="ICO")
        print(f"成功将 {jpg_path} 转换为 {ico_path}")
        return True
    except Exception as e:
        print(f"转换失败: {e}")
        return False

if __name__ == "__main__":
    # 检查1.jpg是否存在
    if os.path.exists("1.jpg"):
        convert_jpg_to_ico("1.jpg", "app_icon.ico")
    else:
        print("未找到 1.jpg 文件")