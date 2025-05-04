from linebot.models import FlexSendMessage, MessageEvent, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot import AsyncLineBotApi, WebhookParser
from fastapi import Request, FastAPI, HTTPException
import logging
import cv2
import re
import aiohttp
import numpy as np
import os
import sys
import tempfile
from dotenv import load_dotenv
from tensorflow.keras.models import load_model
from PIL import Image
from io import BytesIO
from sklearn.preprocessing import LabelEncoder
from fastapi import Request, Response, HTTPException
from linebot.exceptions import InvalidSignatureError
from fastapi import FastAPI, Request, HTTPException
from linebot.models import MessageEvent, TextSendMessage
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


# โหลดตัวแปร environment
load_dotenv()

# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ตรวจสอบตัวแปร environment
channel_secret = os.getenv('ChannelSecret')
channel_access_token = os.getenv('ChannelAccessToken')

if not channel_secret or not channel_access_token:
    logging.error("Missing LINE channel credentials")
    sys.exit(1)

# โหลดโมเดล Keras
try:
    model = load_model('model_final_1.h5')
    logging.info("Model loaded successfully")
except Exception as e:
    logging.error(f"Error loading model: {e}")
    sys.exit(1)

# ข้อมูลโรคใบอ้อย (รวมคลาส Unknown)
disease_info = {
   "Healthy": """
🌿 อ้อยสุขภาพดี

✅ ลักษณะของอ้อยสุขภาพดี
- ใบมีสีเขียวสดใส สม่ำเสมอ  
- ลำต้นแข็งแรง ไม่มีรอยแตกหรือจุดผิดปกติ  
- การเจริญเติบโตเป็นไปตามปกติ  

🛡️ วิธีดูแลรักษา
- ให้น้ำและปุ๋ยอย่างเหมาะสม  
- ตรวจสอบแปลงอ้อยเป็นประจำ  
- กำจัดวัชพืชและศัตรูพืช  
    """,
    "Mosaic": """
🌿 โรคใบด่างอ้อย 

⚠️ อาการของโรค
- ใบอ้อยมีลายด่างสีเขียวอ่อนสลับเขียวเข้มเป็นทาง  
- ใบอาจบิดเบี้ยวหรือเจริญเติบโตช้ากว่าปกติ  
- อ้อยที่เป็นโรครุนแรงอาจแคระแกร็น และให้ผลผลิตต่ำ  

🔎 สาเหตุที่เกิดโรค 
- เกิดจาก เชื้อไวรัส Sugarcane Mosaic Virus (SCMV)
- ติดต่อผ่าน เพลี้ยอ่อน (Aphids) ที่เป็นพาหะ  
- แพร่กระจายผ่านพันธุ์อ้อยที่ติดเชื้อ  

🛡️ วิธีป้องกันโรค  
- ใช้พันธุ์อ้อยต้านทานโรค เช่น KK3, LK92-11 
- ควบคุมเพลี้ยอ่อนโดยใช้สารชีวภัณฑ์  
- หลีกเลี่ยงการใช้พันธุ์อ้อยจากแหล่งที่มีโรคระบาด  

💊 สารเคมีที่ใช้
- อิมิดาคลอพริด (Imidacloprid)
- เชื้อรา Beauveria bassiana  

🌱 ระยะแรกเริ่มของโรค
- พบอาการในช่วง ต้นอ้อยอายุ 1-2 เดือน
- ใบเริ่มมีจุดด่างเป็นแถบคล้ายลายโมเสค  

📃 แหล่งอ้างอิง:
- [กรมวิชาการเกษตร](https://www.doa.go.th)  
- [วารสารโรคพืชและจุลชีววิทยา](https://www.tjpp.org)  
    """,
    "Rust": """
🌿 โรคราสนิม (Rust Disease)

⚠️ อาการของโรค  
- มีจุดสีน้ำตาลหรือส้มกระจายทั่วใบ  
- ใบอ้อยเหลืองและแห้งก่อนเวลา  
- พบเชื้อราละอองสีน้ำตาลคล้ายสนิม  

🔎 สาเหตุที่เกิดโรค
- เกิดจากเชื้อรา Puccinia kuehnii 
- แพร่กระจายผ่านลมและน้ำฝน 
 
🛡️ วิธีป้องกันโรค 
- ใช้พันธุ์อ้อยต้านทาน เช่น K88-92, Suphanburi 50
- หลีกเลี่ยงปลูกอ้อยแน่นเกินไป เพื่อให้อากาศถ่ายเท  

💊 สารเคมีที่ใช้ 
- ไตรฟอกซี่สโตรบิน (Trifloxystrobin) 
- โพรพิเนบ (Propineb)

🌱 ระยะแรกเริ่มของโรค
- พบอาการในช่วง อ้อยอายุ 2-3 เดือน  
- เริ่มจากจุดเล็ก ๆ ก่อนขยายเป็นแผลสีน้ำตาล  

📃 แหล่งอ้างอิง:
- [วารสารเกษตรศาสตร์](https://www.agri.kps.ku.ac.th)  
- [งานวิจัยของมหาวิทยาลัยเกษตรศาสตร์](https://www.ku.ac.th)  
    """,
    "RedRot": """
🌿 โรคเหี่ยวเน่าแดง (Red Rot Disease)

⚠️ อาการของโรค
- ใบเหี่ยวแห้ง และมีสีเหลือง  
- ลำต้นอ้อยมีรอยแตก และเนื้อในเป็นสีแดง-ดำ  
- มีกลิ่นเน่าเหม็น  

🔎 สาเหตุที่เกิดโรค
- เกิดจากเชื้อรา Colletotrichum falcatum 
- เชื้อแพร่กระจายในดินและเข้าทำลายทางราก  

🛡️ วิธีป้องกันโรค
- ใช้พันธุ์อ้อยทนโรค เช่น KPS94-13, U-Thong 2
- ปลูกอ้อยหมุนเวียนกับพืชอื่นเพื่อลดการสะสมของเชื้อ  

💊 สารเคมีที่ใช้  
- แมนโคเซบ (Mancozeb) 
- คาร์เบนดาซิม (Carbendazim) 

🌱 ระยะแรกเริ่มของโรค 
- พบอาการใน อ้อยอายุ 3-5 เดือน 
- ใบเริ่มเหี่ยวเฉา และลำต้นอ้อยเริ่มเป็นรอยแตก  

📃 แหล่งอ้างอิง: 
- [กรมวิชาการเกษตร(https://www.doa.go.th), 
- [IRRI (International Rice Research Institute)(https://www.irri.org)  
    """,
    "Yellow": """
🌿 โรคใบไหม้ (Leaf Scald Disease)

⚠️ อาการของโรค 
- ใบมีรอยไหม้เป็นทางยาวคล้ายถูกน้ำร้อนลวก  
- อ้อยเจริญเติบโตช้า และอาจตายต้น  

🔎 สาเหตุที่เกิดโรค
- เกิดจากเชื้อแบคทีเรีย Xanthomonas albilineans
- ติดต่อผ่านพันธุ์อ้อยและแมลงพาหะ  

🛡️ วิธีป้องกันโรค 
- ใช้พันธุ์อ้อยที่ทนทาน เช่น **Suphanburi 7**  
- แช่ท่อนพันธุ์ในน้ำร้อน 50°C นาน 30 นาที เพื่อลดเชื้อ  

💊 สารเคมีที่ใช้ 
- ไม่มีสารเคมีรักษาโดยตรง ต้องใช้การจัดการแปลงแทน  

🌱 ระยะแรกเริ่มของโรค 
- พบอาการเมื่ออ้อยเริ่มแตกใบใหม่  
- ใบมีรอยซีดขาวก่อนเปลี่ยนเป็นสีน้ำตาลไหม้  

📃 แหล่งอ้างอิง: 
- [กรมวิชาการเกษตร](https://www.doa.go.th)  
- [FAO (Food and Agriculture Organization)(https://www.fao.org)  
    """
}

# ชื่อโรคภาษาไทยสำหรับแสดงรายการ
disease_display_names = {
    "Healthy": "อ้อยสุขภาพดี",
    "Mosaic": "โรคใบด่างอ้อย",
    "Rust": "โรคราสนิม",
    "RedRot": "โรคเหี่ยวเน่าแดง",
    "Yellow": "โรคใบไหม้",
    "Unknown": "ไม่ทราบโรค"
}

app = FastAPI()
session = aiohttp.ClientSession()
line_bot_api = AsyncLineBotApi(channel_access_token, AiohttpAsyncHttpClient(session))
parser = WebhookParser(channel_secret)

# ตั้งค่า LabelEncoder
label_encoder = LabelEncoder()
label_encoder.classes_ = np.array(["Healthy", "Mosaic", "RedRot", "Rust", "Yellow", "Unknown"])

def remove_background(img):
    """ตัดพื้นหลังใบอ้อยและเปลี่ยนเป็นสีดำ"""
    try:
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # กำหนดช่วงสีเขียวของใบอ้อย
        lower_green = np.array([25, 40, 40])
        upper_green = np.array([95, 255, 255])
        
        # สร้าง mask ด้วย inRange
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # ปรับปรุง mask ด้วย morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # หา contour ที่ใหญ่ที่สุด
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)
        
        # สร้างภาพใหม่โดยเปลี่ยนพื้นหลังเป็นสีดำ
        result = img.copy()
        result[mask == 0] = [0, 0, 0]  # ตั้งค่าพื้นหลังเป็นสีดำ
        
        return result, mask
    except Exception as e:
        logging.error(f"Background removal error: {e}")
        return img, None

def check_image_characteristics(img):
    """ตรวจสอบคุณสมบัติพื้นฐานของภาพ (ปรับปรุงใหม่)"""
    try:
        # ตรวจสอบขนาดภาพ
        if img.shape[0] < 100 or img.shape[1] < 100:
            return False
        
        # ตัดพื้นหลังและรับ mask
        _, mask = remove_background(img)
        
        if mask is None:
            return False
        
        # ตรวจสอบพื้นที่สีเขียว
        green_pixels = cv2.countNonZero(mask)
        green_ratio = green_pixels / (img.shape[0] * img.shape[1])
        
        return green_ratio > 0.2
    except Exception as e:
        logging.error(f"Image check error: {e}")
        return False

def preprocess_image(image_data):
    """ปรับปรุงการพรีโพรเซสภาพ"""
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # ตรวจสอบคุณสมบัติภาพ
        if not check_image_characteristics(img):
            return None, "ภาพไม่ตรงเงื่อนไขการวิเคราะห์"

        # ปรับขนาดและสี
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (224, 224))
        return np.expand_dims(img, axis=0), None
    except Exception as e:
        logging.error(f"Preprocessing error: {e}")
        return None, "ข้อผิดพลาดในการประมวลผลภาพ"

def calculate_ood_score(predictions):
    """คำนวณคะแนน Out-of-Distribution"""
    epsilon = 1e-10
    entropy = -np.sum(predictions * np.log(predictions + epsilon))
    return entropy

async def classify_image(image_data):
    """กระบวนการจำแนกภาพแบบปรับปรุง"""
    try:
        # พรีโพรเซสและตรวจสอบภาพ
        processed_image, error_msg = preprocess_image(image_data)
        if error_msg:
            return error_msg

        # ทำนายผล
        prediction = model.predict(processed_image)[0]
        
        # ตรวจสอบ OOD
        ood_score = calculate_ood_score(prediction)
        if ood_score > 1.2:
            return disease_info["Unknown"]

        # ตรวจสอบความมั่นใจ
        confidence = np.max(prediction) * 100
        if confidence < 65:
            return disease_info["Unknown"]

        # ระบุคลาส
        predicted_class = np.argmax(prediction)
        disease_name = label_encoder.inverse_transform([predicted_class])[0]

        return (
            f"ผลการวินิจฉัย: {disease_name}\n"
            f"ความแม่นยำ: {confidence:.2f}%\n\n"
            f"{disease_info.get(disease_name, disease_info['Unknown'])}"
        )
    except Exception as e:
        logging.error(f"Classification error: {e}")
        return disease_info["Unknown"]
    


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

app = FastAPI()
@app.post("/callback")
async def handle_callback(request: Request):
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    
    try:
        events = parser.parse(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            continue
 
        elif event.message.type == "text":
            msg = event.message.text
            
            # กรณีทักทาย
            if msg.strip() == "สวัสดี":
                response = "น้องอ้อยใจสวัสดีค่ะ สามารถส่งรูปภาพใบอ้อยเพื่อทำนายโรคหรือส่งคำถามเกี่ยวกับโรคอ้อยมาได้เลยค่ะ"
            
            # กรณีสอบถามรายชื่อโรค
            elif any(kw in msg for kw in ["โรคอะไรบ้าง", "มีโรคอะไร", "โรคมีอะไร", "โรคอ้อย","มีโรคไรบ้าง""โรคอ้อยที่พบบ่อยในประเทศไทย", 
             "โรคอ้อยที่พบบ่อย", "โรคอ้อย", "โรคอ่อย", "อ้อย", "โรค", "อ้อยที่เป็นโรค", "โรคอ้อยที่อันตราย", 
            "โรคอ้อยมีกี่โรค", "อ้อยเป็นโรคอะไรได้บ้าง", "อ้อยเป็นโรคอะไร", "โรคที่พบบ่อยในอ้อย", "โรคที่อ้อยเป็นได้", 
            "โรคของอ้อยมีอะไรบ้าง", "อ้อยป่วยเป็นอะไรได้บ้าง", "โรคพืชอ้อย", "โรคพืชในอ้อย", "อ้อยมีโรคอะไรได้บ้าง", 
            "อ้อยเป็นโรคอะไรได้", "อ้อยเกิดโรคอะไรได้บ้าง", "อ้อยมีปัญหาสุขภาพอะไร", "อ้อยเสียหายจากโรคอะไร", 
            "โรคที่เกิดกับอ้อย", "โรคที่พบในอ้อย", "โรคเกี่ยวกับอ้อย", "โรคสำคัญในอ้อย", "ปัญหาโรคในอ้อย", 
            "โรคที่ทำให้อ้อยตาย", "อ้อยเป็นโรคอะไรถึงตาย", "โรคในอ้อยมีอะไรที่ร้ายแรง", "อ้อยเจอโรคอะไรได้บ้าง"]):
                diseases = [disease_display_names[d] for d in disease_info.keys() if d != "Unknown"]
                disease_list = "\n- ".join(diseases)
                response = f"📜 โรคในอ้อยที่สามารถวิเคราะห์ได้มีดังนี้:\n- {disease_list}\n\n🖼️ สามารถส่งรูปภาพใบอ้อยเพื่อวิเคราะห์โรคได้ค่ะ"
             # กรณีพูดถึงโรคหรืออ้อยแต่ไม่ระบุรายละเอียด
            elif any(kw in msg for kw in ["ใบด่างอ้อย","โรคใบด่าง","Mosaic","mosaic","ใบด่าง","ด่าง","โรคใบด่างอ้อย"]):
                response = "รวมคำตอบโรคใบด่างอ้อย(Mosaic)ให้แล้วค่ะ" \
                            "⚠️ อาการของโรค" \
                            "- ใบอ้อยมีลายด่างสีเขียวอ่อนสลับเขียวเข้มเป็นทาง" \
                            "- ใบอาจบิดเบี้ยวหรือเจริญเติบโตช้ากว่าปกติ  " \
                            "- อ้อยที่เป็นโรครุนแรงอาจแคระแกร็น และให้ผลผลิตต่ำ  " \
                            "🔎 สาเหตุที่เกิดโรค " \
                            "- เกิดจาก เชื้อไวรัส Sugarcane Mosaic Virus (SCMV)" \
                            "- ติดต่อผ่าน เพลี้ยอ่อน (Aphids) ที่เป็นพาหะ  " \
                            "- แพร่กระจายผ่านพันธุ์อ้อยที่ติดเชื้อ  " \
                            "🛡️ วิธีป้องกันโรค  " \
                            "- ใช้พันธุ์อ้อยต้านทานโรค เช่น KK3, LK92-11 " \
                            "- ควบคุมเพลี้ยอ่อนโดยใช้สารชีวภัณฑ์  " \
                            "- หลีกเลี่ยงการใช้พันธุ์อ้อยจากแหล่งที่มีโรคระบาด  " \
                            "💊 สารเคมีที่ใช้" \
                            "- อิมิดาคลอพริด (Imidacloprid)" \
                            "- เชื้อรา Beauveria bassiana  " \
                            "🌱 ระยะแรกเริ่มของโรค" \
                            "- พบอาการในช่วง ต้นอ้อยอายุ 1-2 เดือน" \
                            "- ใบเริ่มมีจุดด่างเป็นแถบคล้ายลายโมเสค  " \
                            "📃 แหล่งอ้างอิง:" \
                            "- [กรมวิชาการเกษตร](https://www.doa.go.th)  " \
                            "- [วารสารโรคพืชและจุลชีววิทยา](https://www.tjpp.org)"

            # กรณีพูดถึงโรคหรืออ้อยแต่ไม่ระบุรายละเอียด
            elif any(kw in msg for kw in ["โรค", "อ้อย"]):
                response = "กรุณาส่งภาพใบอ้อยเพื่อวิเคราะห์โรค"
            
            # กรณีข้อความทั่วไป
            else:
                response = "ระบบนี้ใช้สำหรับวิเคราะห์โรคอ้อยเท่านั้น"
            
            await line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response))
        elif event.message.type == "image":
            try:
                message_content = await line_bot_api.get_message_content(event.message.id)
                image_data = b''
                
                async for chunk in message_content.iter_content():
                    image_data += chunk

                result = await classify_image(image_data)
                
                await line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=result))
                
            except Exception as e:
                logging.error(f"Image processing error: {e}")
                await line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=disease_info["Unknown"]))
    return {"status": "ok"}