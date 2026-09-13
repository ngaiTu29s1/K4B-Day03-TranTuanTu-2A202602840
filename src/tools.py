"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND (VINLAB CANTEEN & FASTPASS DISPATCHER)
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
Đề tài: Trợ lý Điều Phối Suất Ăn & Phân Luồng FastPass Nhà Ăn VinLab
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Tra cứu trạng thái nhà ăn, 2 Bếp và tình trạng vé của học viên
    {
        "name": "check_canteen_and_tickets",
        "description": "Tra cứu thông tin nhà ăn VinLab: số ghế trống (sức chứa 500), thời gian chờ & hàng đợi của 2 Bếp cạnh tranh (Bếp 1 vs Bếp 2), thực đơn hôm nay, và thông tin thẻ vé (vé tháng còn bao nhiêu lỗ bấm / vé ngày chưa thanh toán) của học viên.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã số học viên cần tra cứu (ví dụ: '2A202602840' hoặc 'SV2026001')"
                },
                "preferred_kitchen": {
                    "type": "string",
                    "enum": ["bep_1", "bep_2"],
                    "description": "Tùy chọn lọc theo bếp: 'bep_1' (Nhà thầu A - Cơm phần truyền thống) hoặc 'bep_2' (Nhà thầu B - Bún mì & Eat Clean Healthy)"
                }
            },
            "required": ["student_id"]
        }
    },
    
    # Tool 2: Đặt trước suất ăn trưa và cấp mã FastPass nhận đồ nhanh tại làn ưu tiên
    {
        "name": "order_meal_fastpass",
        "description": "Đặt trước suất ăn trưa và cấp mã FastPass nhận đồ nhanh tại làn ưu tiên nhà ăn VinLab. Tự động trừ lượt vé tháng (tránh bấm lỗ thủ công) hoặc tạo thông tin VietQR chuyển khoản nhanh cho chủ bếp (tránh xếp hàng chờ đối chiếu). Hỗ trợ chọn ăn tại chỗ hoặc mang về phòng tự học khi nhà ăn quá tải ghế.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã số học viên đặt suất ăn (ví dụ: '2A202602840')"
                },
                "kitchen_id": {
                    "type": "string",
                    "enum": ["bep_1", "bep_2"],
                    "description": "Mã bếp phục vụ: 'bep_1' (Cơm phần truyền thống) hoặc 'bep_2' (Bún mì & Eat Clean)"
                },
                "pickup_time": {
                    "type": "string",
                    "description": "Khung giờ nhận đồ theo phân luồng 15 phút để tránh dồn 1000 người (ví dụ: '13:05', '13:20', '13:35')"
                },
                "dining_option": {
                    "type": "string",
                    "enum": ["dine_in", "takeaway"],
                    "description": "Hình thức dùng bữa: 'dine_in' (ngồi ăn tại chỗ nếu còn ghế) hoặc 'takeaway' (đóng hộp mang về phòng tự học khi nhà ăn quá tải 500 ghế)"
                },
                "meal_item": {
                    "type": "string",
                    "description": "Tên món ăn muốn đặt (ví dụ: 'Cơm sườn nướng mật ong', 'Bún chả Hà Nội', 'Suất Eat Clean ức gà')"
                }
            },
            "required": ["student_id", "kitchen_id", "pickup_time", "dining_option"]
        }
    },

    # Compatibility Tool: schedule_appointment (đáp ứng tiêu chuẩn kiểm thử chung của starter kit)
    {
        "name": "schedule_appointment",
        "description": "Đặt lịch hẹn tư vấn học vụ hoặc điều phối lịch ăn trưa với Cố vấn/Quản trị viên VinUni.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần đặt lịch (ví dụ: '2A202602840' hoặc 'SV2026001')"
                },
                "datetime_str": {
                    "type": "string",
                    "description": "Thời gian hẹn (ví dụ: '13:10 15/09/2026')"
                },
                "advisor_name": {
                    "type": "string",
                    "description": "Tên cố vấn hoặc quản lý phụ trách"
                }
            },
            "required": ["student_id", "datetime_str", "advisor_name"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

# Dữ liệu thực tế nhà ăn VinLab (Ước lượng qua số lượt quẹt thẻ 15 phút gần nhất & cảm biến lối vào)
CANTEEN_DB = {
    "status": {
        "total_seats": 500,
        "occupancy_level": "CAO ĐIỂM (~90% công suất)",
        "seats_status": "Gần kín chỗ (ước tính chỉ còn khoảng 30 - 40 ghế rải rác)",
        "capacity_alert": "CẢNH BÁO: Nhà ăn đang ở mức tải cao điểm (~90% ghế). Khuyến nghị học viên chọn TAKEAWAY (đóng hộp) mang về phòng tự học để không phải chờ ghế!",
        "measurement_source": "Dữ liệu ước lượng tự động qua cảm biến lối vào & số lượt quét vé 15 phút gần nhất",
        "peak_window": "13:00 - 14:00 (1000 học viên cùng tan ca sáng)"
    },
    "kitchens": {
        "bep_1": {
            "name": "Bếp 1 (Cơm phần truyền thống)",
            "traffic_level": "ÙN Ứ CAO ĐIỂM",
            "est_wait_minutes": 20,
            "status": "RẤT ĐÔNG (Xếp hàng dài, ước tính chờ 15 - 25 phút)",
            "today_menu": [
                {"name": "Cơm sườn nướng mật ong", "price": "35.000đ", "status": "CÒN HÀNG"},
                {"name": "Cơm gà xối mỡ giòn rụm", "price": "35.000đ", "status": "CÒN HÀNG"},
                {"name": "Cơm cá hồi kho tộ", "price": "40.000đ", "status": "SẮP HẾT"}
            ]
        },
        "bep_2": {
            "name": "Bếp 2 (Bún mì & Healthy)",
            "traffic_level": "THÔNG THOÁNG",
            "est_wait_minutes": 4,
            "status": "THÔNG THOÁNG (Ước tính chờ dưới 5 phút - KHUYÊN DÙNG ĐỂ KỊP NGHỈ TRƯA)",
            "today_menu": [
                {"name": "Bún chả Hà Nội than hoa", "price": "35.000đ", "status": "CÒN HÀNG"},
                {"name": "Mì gà tần thảo mộc nạp năng lượng", "price": "40.000đ", "status": "CÒN HÀNG"},
                {"name": "Suất cơm Eat Clean ức gà sốt bơ đậu phộng", "price": "40.000đ", "status": "CÒN HÀNG"}
            ]
        }
    },
    "students": {
        "2A202602840": {
            "full_name": "Trần Tuấn Tú",
            "cohort": "K4B (Lớp Chiều, học 9h-18h)",
            "ticket_type": "VE_THANG",
            "card_id": "PASS-K4B-2A202602840",
            "total_punches": 30,
            "remaining_punches": 18,
            "ticket_status": "HỢP LỆ (Còn 18 lượt bấm lỗ)",
            "payment_method": "Vé tháng đã trả trước - Hệ thống tự động trừ lượt điện tử (không cần chủ bấm lỗ thủ công)"
        },
        "SV2026001": {
            "full_name": "Nguyễn Văn An",
            "cohort": "AI-K4A",
            "ticket_type": "VE_THANG",
            "card_id": "PASS-K4A-SV2026001",
            "total_punches": 30,
            "remaining_punches": 5,
            "ticket_status": "HỢP LỆ (Còn 5 lượt bấm lỗ)",
            "payment_method": "Vé tháng - Sắp hết lượt, cần gia hạn tháng tới"
        },
        "SV2026002": {
            "full_name": "Trần Thị Bình",
            "cohort": "AI-K4A",
            "ticket_type": "VE_NGAY",
            "ticket_status": "CHƯA MUA VÉ TRƯỚC",
            "payment_method": "Chuyển khoản QR Banking trực tiếp cho chủ quán (Hệ thống sẽ cấp VietQR tự động để không cần đứng đối chiếu)"
        }
    }
}


def execute_check_canteen_and_tickets(student_id: str, preferred_kitchen: str = None) -> str:
    """Thực thi tra cứu thông tin sức chứa, 2 bếp và vé học viên"""
    sid = student_id.strip().upper()
    student = CANTEEN_DB["students"].get(sid)
    
    if not student:
        return json.dumps({
            "status": "NOT_FOUND",
            "student_id": student_id,
            "message": f"Không tìm thấy dữ liệu học viên mã '{student_id}' trong hệ thống VinLab Canteen. Vui lòng kiểm tra lại mã số."
        }, ensure_ascii=False)
    
    kitchens_info = {}
    if preferred_kitchen and preferred_kitchen in CANTEEN_DB["kitchens"]:
        kitchens_info[preferred_kitchen] = CANTEEN_DB["kitchens"][preferred_kitchen]
    else:
        kitchens_info = CANTEEN_DB["kitchens"]
        
    return json.dumps({
        "status": "SUCCESS",
        "student_id": sid,
        "student_info": student,
        "canteen_capacity": CANTEEN_DB["status"],
        "kitchens_traffic": kitchens_info,
        "dispatcher_advice": (
            "GỢI Ý TỪ HỆ THỐNG PHÂN LUỒNG: Bếp 1 đang ở mức tải cao điểm ùn ứ (ước tính chờ 15 - 25 phút). "
            "Bếp 2 đang thông thoáng (ước tính chờ dưới 5 phút). Nhà ăn gần kín chỗ (~90%), nên chọn 'takeaway' (đóng hộp) "
            "để đem về phòng tự học ăn và nghỉ ngơi trọn vẹn 1 tiếng!"
        )
    }, ensure_ascii=False)


def execute_order_meal_fastpass(
    student_id: str,
    kitchen_id: str,
    pickup_time: str,
    dining_option: str,
    meal_item: str = "Suất ăn tiêu chuẩn"
) -> str:
    """Thực thi đặt trước suất ăn và cấp mã FastPass nhận đồ nhanh tại làn ưu tiên"""
    sid = student_id.strip().upper()
    kid = kitchen_id.strip().lower()
    
    kitchen_data = CANTEEN_DB["kitchens"].get(kid)
    if not kitchen_data:
        return json.dumps({
            "status": "ERROR",
            "message": f"Mã bếp '{kitchen_id}' không hợp lệ! Vui lòng chọn 'bep_1' hoặc 'bep_2'."
        }, ensure_ascii=False)
        
    student = CANTEEN_DB["students"].get(sid, {
        "full_name": f"Học viên {sid}",
        "ticket_type": "VE_NGAY",
        "payment_method": "VietQR chuyển khoản trực tiếp"
    })
    
    fastpass_code = f"FASTPASS-{kid.upper()}-{pickup_time.replace(':', '')}-{sid[-4:]}"
    
    # Xử lý theo loại vé
    if student.get("ticket_type") == "VE_THANG":
        remaining = student.get("remaining_punches", 0)
        if remaining > 0:
            ticket_action = f"Vé tháng hợp lệ (còn {remaining}/30 lượt). Quẹt mã tại quầy để hệ thống tự động trừ 1 lượt ăn (không cần bấm lỗ thủ công)."
            payment_info = f"Vé tháng (còn {remaining} lượt)"
        else:
            ticket_action = "CẢNH BÁO: Thẻ vé tháng của bạn ĐÃ HẾT LƯỢT BẤM (0/30). Vui lòng thanh toán 35.000đ khi nhận đồ tại quầy hoặc gia hạn thẻ mới."
            payment_info = "35.000đ (thanh toán khi nhận do hết lượt vé)"
    else:
        ticket_action = "Vé ngày: Thanh toán 35.000đ khi nhận đồ hoặc quét QR tại quầy bếp."
        payment_info = "35.000đ (thanh toán khi nhận đồ)"

    dining_desc = "Mang về phòng tự học (Takeaway box)" if dining_option == "takeaway" else "Ăn tại chỗ (Dine-in khay cơm)"

    return json.dumps({
        "status": "SUCCESS",
        "fastpass_code": fastpass_code,
        "student_id": sid,
        "student_name": student.get("full_name"),
        "kitchen": kitchen_data["name"],
        "meal_item": meal_item,
        "pickup_time": pickup_time,
        "dining_option": dining_desc,
        "ticket_processing": ticket_action,
        "payment_status": payment_info,
        "pickup_instructions": f"Đúng {pickup_time}, hãy đến CỬA FAST-TRACK CỦA {kitchen_data['name'].upper()}, xuất trình mã {fastpass_code} để quét nhận đồ trong 30 giây (quét xong trừ lượt, không cần xếp hàng)!"
    }, ensure_ascii=False)


def execute_schedule_appointment(student_id: str, datetime_str: str, advisor_name: str = "Quản lý Căn tin VinLab") -> str:
    """Thực thi đặt lịch hẹn tư vấn học vụ hoặc điều phối lịch ăn"""
    return json.dumps({
        "status": "SUCCESS",
        "booking_id": f"BK-{student_id}-99",
        "student_id": student_id,
        "datetime": datetime_str,
        "advisor": advisor_name,
        "message": f"Đặt lịch thành công cho học viên {student_id} với {advisor_name} vào lúc {datetime_str}."
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "check_canteen_and_tickets": execute_check_canteen_and_tickets,
    "order_meal_fastpass": execute_order_meal_fastpass,
    "schedule_appointment": execute_schedule_appointment,
    "academic_query": execute_check_canteen_and_tickets  # Alias tương thích
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
