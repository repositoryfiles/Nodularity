# JIS G5502-2022 ISO法、JIS法による球状化率の判定
# coding: utf-8
import tkinter
from tkinter import filedialog
import cv2
import os
import sys
import datetime
import math

# https://www.rectus.co.jp/archives/18
# pythonのprintでエラーになるときの対応
import io
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 環境設定
iDir='C:/Data' # 画像ファイルが格納されているフォルダ
pic_width=1920 # 入力画像のサイズによらず、画像処理や出力画像はこの幅に設定
    # pic_height（高さ）は入力画像の幅と高さの比から計算
min_grainsize=0.0071 # 画像の幅に対する黒鉛の最小長さ（撮影した画像に応じて設定が必要）
    # min_grainsize=0.007はサンプル画像に対する値である。
    # サンプル画像は幅142mmに表示させると、倍率100倍の組織画像になる。
    # この場合、黒鉛の最小長さ（10μm）は1mmとなる。1mm÷142mm=0.007→min_grainsize
marumi_ratio = 0.6 #iso法で形状ⅤとⅥと判定する丸み係数のしきい値

# ダイアログ形式によるファイル選択
def get_picture_filenames():
    root=tkinter.Tk()
    root.withdraw()
    fTyp = [("jpg", "*.jpg"), ("BMP", "*.bmp"), ("png", "*.png"), ("tiff", "*.tif")] 
    filenames = filedialog.askopenfilenames(title='画像ファイルを選んでください', filetypes=fTyp, initialdir=iDir) 
    return filenames

# contoursからmin_grainsize未満の小さい輪郭と、画像の端に接している輪郭を除いてcoutours1に格納
def select_contours(contours, pic_width, pic_height, min_grainsize):
    contours1 = []
    for e, cnt in enumerate(contours):
        x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(cnt)
        (x_circle, y_circle), radius_circle = cv2.minEnclosingCircle(cnt)
        if int(pic_width * min_grainsize) <= 2 * radius_circle \
            and 0 < int(x_rect) and 0 < int(y_rect) and \
            int(x_rect + w_rect) < pic_width and int(y_rect + h_rect) < pic_height:
            contours1.append(cnt)  
    return contours1

# 輪郭の長軸の中心座標と、最遠点対の半分の長さを求める（キャリパ法）
def get_graphite_length(hull):
    max_distance = 0
    for i, hull_x in enumerate(hull):
        for j, hull_y in enumerate(hull):
            if j + 1 < len(hull) and i != j + 1:
                dis_x = hull[j+1][0][0] - hull[i][0][0]
                dis_y = hull[j+1][0][1] - hull[i][0][1]
                dis = math.sqrt(dis_x**2 + dis_y**2)
                if dis > max_distance:
                    max_distance = dis # 最遠点対の距離を更新
                    x = dis_x * 0.5 + hull[i][0][0] # 最遠点対の中点を更新
                    y = dis_y * 0.5 + hull[i][0][1] # 最遠点対の中点を更新
    return(x, y, max_distance * 0.5) # 最遠点対の半分の長さ（円の半径）

def main():
    # 画像ファイル名の取り込み
    filenames = get_picture_filenames()
    if filenames == "":
        sys.exit()

    # 画像ファイルごとの球状化率はこの変数に格納
    nodularity_ISO = []
    nodularity_JIS = []

    for filename in filenames:

        # 画像ファイルの読み込み、サイズ取得（パス名に全角があるとエラーになる）
        img_color_ISO= cv2.imread(filename) # カラーで出力表示させるためカラーで読み込み
        img_height, img_width, channel = img_color_ISO.shape # 画像のサイズ取得
        
        # 画像処理や出力画像のサイズ計算（pic_width, pic_height）
        pic_height=int(pic_width * img_height / img_width)
        img_color_ISO = cv2.resize(img_color_ISO, (pic_width, pic_height)) # 読み込んだ画像ファイルのサイズ変換
        img_color_JIS = img_color_ISO.copy() #img_colorのコピーの作成
        
        # カラー→グレー変換、白黒反転の二値化、輪郭の検出、球状化率の評価に用いる輪郭の選別
        img_gray = cv2.cvtColor(img_color_ISO, cv2.COLOR_BGR2GRAY)
        ret, img_inv_binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
        contours, hierarchy = cv2.findContours(img_inv_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contours1 = select_contours(contours, pic_width, pic_height, min_grainsize) # 球状化率の評価に用いる輪郭をcoutours1に格納

        # 黒鉛の面積と黒鉛の長軸の中心座標、長軸の半分の長さの計算、丸み係数の算出
        sum_graphite_areas = 0
        sum_graphite_areas_5and6 = 0
        num_graphite1 = num_graphite2 = num_graphite3 = num_graphite4 = num_graphite5 = 0

        for i, cnt in enumerate(contours1): 
            graphite_area = cv2.contourArea(cnt)
            sum_graphite_areas += graphite_area
            hull = cv2.convexHull(cnt) # 凸包
            x, y, graphite_radius = get_graphite_length(hull) # 輪郭の長軸の中心座標（x, y）と長軸の半分の長さ(graphite_radius)
            marumi = graphite_area / ((graphite_radius ** 2) * math.pi) #丸み係数

            # ISO法による形状ⅤとⅥの黒鉛の判定し、それらの黒鉛の輪郭を赤色で描画
            if marumi >= marumi_ratio:
                sum_graphite_areas_5and6 += graphite_area
                cv2.drawContours(img_color_ISO, contours1, i, (0, 0, 255), 2)

            # JIS法による形状分類
            if marumi <= 0.2:
                num_graphite1 += 1
                cv2.drawContours(img_color_JIS, contours1, i, (255, 255, 0), 2) #水色
            if 0.2 < marumi <= 0.4:
                num_graphite2 += 1
                cv2.drawContours(img_color_JIS, contours1, i, (0, 255, 0), 2) #緑
            if 0.4 < marumi <= 0.7:
                num_graphite3 += 1
                cv2.drawContours(img_color_JIS, contours1, i, (128, 0, 128), 2) #紫
            if 0.7 < marumi <= 0.8:
                num_graphite4 += 1
                cv2.drawContours(img_color_JIS, contours1, i, (255, 0, 0), 2) #青
            if 0.8 < marumi:
                num_graphite5 += 1
                cv2.drawContours(img_color_JIS, contours1, i, (0, 0,255), 2) #赤
                    
        # 球状化率（ISO法）
        nodularity_ISO.append(sum_graphite_areas_5and6 / sum_graphite_areas * 100)
        # 球状化率（JIS法）
        nodularity_JIS.append((0.3 * num_graphite2 + 0.7 * num_graphite3 + 0.9 * num_graphite4 + 1.0 * num_graphite5)/ len(contours1) * 100)
        
        # 画像ファイルの保存
        src = filename
        idx = src.rfind(r'.')
        result_ISO_filename = src[:idx] + "_nodularity(ISO)." + src[idx+1:]
        result_JIS_filename = src[:idx] + "_nodularity(JIS)." + src[idx+1:]
        cv2.imwrite(result_ISO_filename, img_color_ISO)
        cv2.imwrite(result_JIS_filename, img_color_JIS)

    # 球状化率などのデータの保存
    now = datetime.datetime.now()

    output_file = str(os.path.dirname(filenames[0])) + '/nodularity_{0:%Y%m%d%H%M}'.format(now) + ".csv"

    with open(output_file, mode='w') as f1:
        print("最小黒鉛サイズ, {:.3f}".format(min_grainsize), file = f1)
        print("丸み係数のしきい値, {:.3f}".format(marumi_ratio), file = f1)
        print("画像処理と出力画像の幅, {}".format(pic_width), file = f1)
        print("ファイル名, 球状化率_ISO法(%), 球状化率_JIS法(%)", file = f1)
        for i in range(len(filenames)):
            print("{}, {:.2f}, {:.2f}" .format(filenames[i], nodularity_ISO[i], nodularity_JIS[i]), file = f1)

            
if __name__ == "__main__":
    main()
