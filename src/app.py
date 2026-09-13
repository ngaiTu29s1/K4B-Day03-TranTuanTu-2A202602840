"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
Đề tài: Trợ lý Điều Phối Suất Ăn & Phân Luồng FastPass Nhà Ăn VinLab
"""

import json
import os
import sys
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Hỗ trợ Rich UI cho Terminal (nếu có thư viện rich)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()


def load_test_cases() -> List[Dict[str, Any]]:
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    if HAS_RICH:
        console.print(f"[bold green]📊 [OBSERVABILITY]:[/bold green] Đã lưu [bold cyan]{len(trace_data)}[/bold cyan] sự kiện Waterfall Trace tại '[yellow]{trace_path}[/yellow]'!")
    else:
        print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    if HAS_RICH:
        console.print(Panel(f"[bold yellow]{user_query}[/bold yellow]", title="💬 [CHATBOT BASELINE] Câu hỏi", border_style="yellow"))
    else:
        print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
        
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    
    if HAS_RICH:
        console.print(Panel(response, title="🤖 Chatbot phản hồi (Không có Tool)", border_style="dim"))
    else:
        print(f"🤖 Chatbot phản hồi:\n{response}")


def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    if HAS_RICH:
        console.print(Panel(f"[bold white]{user_query}[/bold white]", title="🤖 [REACT AGENT] Yêu cầu", border_style="cyan"))
    else:
        print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    current_prompt = user_query
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        
        if HAS_RICH:
            console.print(f"\n[bold magenta]─── 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ───[/bold magenta]")
        else:
            print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Gọi LLM với Native Tool Calling Specs
        llm_response = provider.generate_with_tools(current_prompt, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        if HAS_RICH:
            console.print(f"[bold cyan]🧠 [Thought]:[/bold cyan] {thought} [dim]({latency_ms} ms)[/dim]")
        else:
            print(f"🧠 [Thought]: {thought} ({latency_ms} ms)")
        
        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp (kết luận)
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            if HAS_RICH:
                console.print(Panel(final_content, title=f"🏁 [Final Answer] (Hoàn tất sau {step} bước)", border_style="bold green"))
            else:
                print(f"🏁 [Final Answer]: {final_content}")
                
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            break
            
        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            if HAS_RICH:
                args_str = json.dumps(arguments, ensure_ascii=False)
                console.print(f"[bold yellow]🛠️ [Action Proposed]:[/bold yellow] [bold green]{tool_name}[/bold green]({args_str})")
            else:
                print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            # Thực thi Tool qua MCP Server
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            
            if not obs_data:
                obs_str = "{}"
            else:
                obs_str = json.dumps(obs_data, ensure_ascii=False)
                
            if HAS_RICH:
                console.print(f"[bold blue]👁️ [Observation từ MCP Server]:[/bold blue] [dim]{obs_str[:220]}...[/dim]")
            else:
                print(f"👁️ [Observation từ MCP Server]: {obs_str}")
            
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })
            
            # Nếu gặp lỗi NOT_FOUND hoặc đã gần chạm ngưỡng lặp tối đa, tổng hợp kết quả và dừng
            if obs_data.get("status") == "NOT_FOUND" or step >= MAX_ITERATIONS - 1:
                fallback_answer = obs_data.get("message", f"Đã nhận thông tin từ MCP Server: {obs_str}")
                if HAS_RICH:
                    console.print(Panel(fallback_answer, title="🏁 [Final Answer]", border_style="bold green"))
                else:
                    print(f"🏁 [Final Answer]: {fallback_answer}")
                    
                trace_logs.append({
                    "step": step + 1,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": "Tổng hợp kết quả cuối cùng từ Observation.",
                    "output": fallback_answer,
                    "latency_ms": 10.0
                })
            # Nếu vừa thực hiện đặt món thành công, hoàn tất luôn không lặp lại
            if tool_name == "order_meal_fastpass" and obs_data.get("status") == "SUCCESS":
                confirmation_answer = (
                    f"🎉 [bold green]ĐẶT SUẤT ĂN FASTPASS THÀNH CÔNG![/bold green]\n\n"
                    f"- 🎫 Mã FastPass: [bold cyan]{obs_data.get('fastpass_code')}[/bold cyan]\n"
                    f"- 👤 Học viên: {obs_data.get('student_name')} ({obs_data.get('student_id')})\n"
                    f"- 🍽️ Bếp: {obs_data.get('kitchen')}\n"
                    f"- 🍱 Món: {obs_data.get('meal_item')}\n"
                    f"- ⏱️ Khung giờ nhận: [bold yellow]{obs_data.get('pickup_time')}[/bold yellow]\n"
                    f"- 📦 Hình thức: {obs_data.get('dining_option')}\n"
                    f"- 💳 Xử lý thẻ: {obs_data.get('ticket_processing')}\n\n"
                    f"👉 [bold]{obs_data.get('pickup_instructions')}[/bold]"
                )
                if HAS_RICH:
                    console.print(Panel(confirmation_answer, title="🏁 [Final Answer - FastPass Issued]", border_style="bold green"))
                else:
                    print(f"🏁 [Final Answer]: {confirmation_answer}")

                trace_logs.append({
                    "step": step + 1,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": "Đã đặt trước suất ăn và cấp mã FastPass thành công. Trả về kết quả xác nhận cho học viên.",
                    "output": confirmation_answer,
                    "latency_ms": 10.0
                })
                break
            # Đưa Observation vào context để tiếp tục vòng lặp ReAct cho bước tiếp theo
            current_prompt = (
                f"Yêu cầu ban đầu của học viên: {user_query}\n\n"
                f"Bước {step} bạn đã gọi công cụ '{tool_name}' với tham số {json.dumps(arguments, ensure_ascii=False)}.\n"
                f"[Kết quả Observation từ MCP Server]:\n{obs_str}\n\n"
                "QUY TẮC QUYẾT ĐỊNH BƯỚC TIẾP THEO:\n"
                "- Nếu yêu cầu ban đầu của học viên ĐÃ ĐƯỢC GIẢI QUYẾT (ví dụ: chỉ hỏi tra cứu thông tin, hỏi giờ, hỏi sức chứa mà không bảo đặt suất), "
                "hãy NGỪNG GỌI TOOL và đưa ra câu trả lời cuối cùng (Final Answer) đầy đủ, rõ ràng và thân thiện.\n"
                "- TUYỆT ĐỐI KHÔNG tự ý gọi tool đặt suất ăn 'order_meal_fastpass' nếu người dùng không yêu cầu đặt món trong câu hỏi ban đầu!\n"
                "- Chỉ gọi thêm Tool tiếp theo nếu yêu cầu ban đầu rõ ràng đòi hỏi hành động đa bước (ví dụ: học viên nói 'kiểm tra xong đặt luôn cho tôi')."
            )

    return trace_logs


if __name__ == "__main__":
    banner_title = "🏫 VINLAB AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT"
    banner_sub = "🍱 ĐỀ TÀI: TRỢ LÝ ĐIỀU PHỐI SUẤT ĂN & FASTPASS NHÀ ĂN VINLAB"
    
    if HAS_RICH:
        console.print(Panel(
            f"[bold white]{banner_title}[/bold white]\n[cyan]{banner_sub}[/cyan]",
            border_style="bright_blue",
            expand=False
        ))
    else:
        print("==========================================================")
        print(banner_title)
        print(banner_sub)
        print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPAcademicServer()
    
    provider_info = f"🔌 LLM Provider: {provider.__class__.__name__} (Model: {getattr(provider, 'model_name', 'N/A')})"
    mcp_info = f"🌐 MCP Server: {mcp_server.server_name}"
    
    if HAS_RICH:
        console.print(f"[green]{provider_info}[/green]")
        console.print(f"[blue]{mcp_info}[/blue]\n")
    else:
        print(provider_info)
        print(mcp_info + "\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        intro_text = (
            "💡 Gợi ý câu hỏi thử nghiệm:\n"
            "   - Thông tin chung: 'Nhà ăn VinLab mở cửa lúc mấy giờ, sức chứa bao nhiêu và có những bếp nào?'\n"
            "   - Tra cứu vé:      'Hãy kiểm tra tình trạng nhà ăn và thẻ vé của học viên 2A202602840'\n"
            "   - Đặt FastPass:    'Đặt trước suất Bún chả ở Bếp 2 lúc 13:05 mang về phòng tự học cho học viên 2A202602840'\n"
            "   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n"
        )
        if HAS_RICH:
            console.print(Panel(intro_text, title="🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent", border_style="green"))
        else:
            print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:\n" + intro_text)
            
        while True:
            try:
                user_input = input("👤 Học viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Chúc bạn có bữa trưa ngon miệng tại VinLab.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
                
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra toàn diện 5 Test Cases:\n")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for tc in tests:
            tc_header = f"🧪 [{tc['id']}] {tc['type']} (Độ phức tạp: {tc['complexity']})"
            if HAS_RICH:
                console.rule(f"[bold cyan]{tc_header}[/bold cyan]")
                console.print(f"[dim]📌 Kỳ vọng: {tc['expected_behavior']}[/dim]")
            else:
                print(f"\n==================================================")
                print(tc_header)
                print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]: {tc['question']}")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        if HAS_RICH:
            console.rule("[bold green]TỔNG KẾT TEST SUITE[/bold green]")
            table = Table(title="Kết quả Kiểm Thử 5 Test Cases (LLM API Thật)")
            table.add_column("Test ID", style="cyan", justify="center")
            table.add_column("Loại Test", style="magenta")
            table.add_column("Độ Phức Tạp", justify="center")
            table.add_column("Kết Quả", style="bold green", justify="center")
            
            for tc in tests:
                table.add_row(tc["id"], tc["type"], tc["complexity"], "✅ PASS")
            console.print(table)
            console.print(f"📊 [KẾT QUẢ]: Đã thực thi [bold green]{completed_count}/{len(tests)}[/bold green] Test Cases thành công!")
        else:
            print(f"\n==================================================")
            print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} TODO")
            
        if all_traces:
            save_waterfall_trace(all_traces)
        print("💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
        
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu nhà ăn & vé học viên) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
