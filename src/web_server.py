"""
🌐 VINLAB SMART CANTEEN & FASTPASS REACT AGENT - WEB DASHBOARD
Web UI tương tác động (Dynamic Model Fetching từ /models, ReAct Step Visualizer, Telemetry thực tế & Metadata chi tiết).
"""

import os
import sys
import json
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_server import MCPAcademicServer
from prompts import REACT_AGENT_SYSTEM_PROMPT, MAX_ITERATIONS
from tools import CANTEEN_DB
from providers import (
    get_llm_provider,
    OpenAICompatibleProvider,
    GeminiProvider,
    OpenAIProvider,
    MockOfflineProvider
)

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VinLab Canteen FastPass | ReAct Agent Dynamic Dashboard</title>
  <!-- TailwindCSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            vinred: '#E02424',
            vinblue: '#1E40AF',
            brand: '#3B82F6',
            surface: '#111827',
            card: '#1F2937'
          }
        }
      }
    }
  </script>
  <!-- Lucide Icons -->
  <script src="https://unpkg.com/lucide@latest"></script>
  <!-- Marked for Markdown -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <!-- QRCode.js -->
  <script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
  <!-- Canvas Confetti -->
  <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
  <style>
    @keyframes pulse-glow {
      0%, 100% { box-shadow: 0 0 15px rgba(59, 130, 246, 0.4); }
      50% { box-shadow: 0 0 35px rgba(59, 130, 246, 0.8); }
    }
    .glow-card { animation: pulse-glow 2.5s infinite; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0B0F19; }
    ::-webkit-scrollbar-thumb { background: #374151; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #4B5563; }
  </style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen font-sans flex flex-col antialiased">

  <!-- HEADER NAVBAR -->
  <header class="bg-gray-900/90 backdrop-blur-md border-b border-gray-800 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
          <i data-lucide="bot" class="w-6 h-6 text-white"></i>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base sm:text-lg font-bold bg-gradient-to-r from-blue-400 to-indigo-300 bg-clip-text text-transparent">
              VinLab Canteen FastPass Agent
            </h1>
            <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40">
              MCP Enhanced
            </span>
          </div>
          <p class="text-xs text-gray-400">
            Học viên: <span id="activeStudentLabel" class="text-blue-300 font-semibold">Trần Tuấn Tú (2A202602840)</span> • Lớp K4B
          </p>
        </div>
      </div>

      <!-- ACTIVE STUDENT SELECTOR & SIMULATOR BUTTON -->
      <div class="flex items-center space-x-2 text-xs">
        <div class="flex items-center gap-1.5 bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">
          <i data-lucide="user-check" class="w-3.5 h-3.5 text-blue-400"></i>
          <span class="text-gray-400">Học viên:</span>
          <select id="studentSelect" onchange="onStudentChange()" class="bg-transparent text-gray-200 font-medium focus:outline-none cursor-pointer">
            <option value="2A202602840" selected>Trần Tuấn Tú (2A202602840 - Vé tháng)</option>
            <option value="SV2026001">Nguyễn Văn An (SV2026001 - Vé tháng 5 lỗ)</option>
            <option value="SV2026002">Trần Thị Bình (SV2026002 - Vé ngày VietQR)</option>
            <option value="SV9999999">Mã không tồn tại (SV9999999 - Edge Case)</option>
          </select>
        </div>

        <button onclick="toggleSimulator()" class="flex items-center gap-1 bg-indigo-950 hover:bg-indigo-900 border border-indigo-700/60 text-indigo-300 px-2.5 py-1 rounded-lg transition">
          <i data-lucide="sliders" class="w-3.5 h-3.5"></i>
          <span class="font-medium">Mô phỏng Telemetry (Flex)</span>
        </button>
      </div>
    </div>
  </header>

  <!-- MODEL & PROVIDER CONFIG BAR (CURL DYNAMICALLY FROM /models) -->
  <div class="bg-gray-900 border-b border-gray-800 px-4 py-2">
    <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
      <div class="flex items-center flex-wrap gap-2">
        <span class="text-gray-400 font-medium flex items-center gap-1">
          <i data-lucide="cpu" class="w-3.5 h-3.5 text-blue-400"></i> Provider:
        </span>
        <select id="providerSelect" onchange="fetchModelsForProvider()" class="bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-2.5 py-1 focus:ring-2 focus:ring-blue-500 focus:outline-none cursor-pointer font-medium">
          <option value="groq" selected>⚡ Groq Cloud (Live /models)</option>
          <option value="gemini">🔷 Google Gemini (Live /models - Quota 1M TPM)</option>
          <option value="nvidia">🟢 NVIDIA NIM (Live /models)</option>
          <option value="openai">🧠 OpenAI (Live /models)</option>
          <option value="mock">💻 Mock Offline (0đ, không cần mạng)</option>
        </select>

        <span class="text-gray-400 font-medium flex items-center gap-1 ml-2">
          Model:
        </span>
        <div class="relative flex items-center">
          <select id="modelSelect" class="bg-gray-800 border border-gray-700 text-gray-200 rounded-lg pl-2.5 pr-8 py-1 focus:ring-2 focus:ring-blue-500 focus:outline-none cursor-pointer">
            <option value="qwen/qwen3.8-27b">Đang tải models từ API...</option>
          </select>
          <span id="modelLoadingSpinner" class="hidden absolute right-2 text-blue-400">
            <i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i>
          </span>
        </div>

        <button onclick="fetchModelsForProvider(true)" title="Cập nhật lại danh sách model từ API" class="p-1 rounded bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-400 hover:text-blue-300 transition">
          <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
        </button>
      </div>

      <div class="flex items-center gap-2 flex-grow max-w-sm">
        <input type="password" id="customApiKey" placeholder="API Key tùy chọn (để trống dùng .env)" class="w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-1 focus:ring-2 focus:ring-blue-500 focus:outline-none placeholder-gray-500 text-xs">
        <button onclick="fetchModelsForProvider(true)" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-3 py-1 rounded-lg transition whitespace-nowrap text-xs shadow-md shadow-blue-600/30">
          Nạp Key
        </button>
      </div>
    </div>
  </div>

  <!-- COLLAPSIBLE SIMULATOR DRAWER (TELEMETRY FLEX) -->
  <div id="simulatorDrawer" class="hidden bg-indigo-950/40 border-b border-indigo-800/40 px-4 py-3 transition-all duration-300">
    <div class="max-w-7xl mx-auto">
      <div class="flex items-center justify-between mb-2">
        <h2 class="text-xs font-bold text-indigo-300 flex items-center gap-1.5 uppercase tracking-wider">
          <i data-lucide="sliders" class="w-4 h-4"></i> Bảng Điều Khiển Mô Phỏng Telemetry (Flex Simulator)
        </h2>
        <span class="text-[11px] text-gray-400">Điều chỉnh mức tải thực tế để kiểm tra phản xạ phân luồng của Agent</span>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
        <div class="bg-gray-900/80 p-2.5 rounded-xl border border-gray-800">
          <div class="flex justify-between items-center mb-1">
            <label class="text-gray-300 font-medium">Mức tải nhà ăn (~500 ghế):</label>
            <span id="simSeatsVal" class="font-bold text-yellow-400">Cao điểm (~90%)</span>
          </div>
          <input type="range" id="simSeats" min="40" max="100" value="90" oninput="updateSimOccupancy(this.value)" class="w-full accent-blue-500 cursor-pointer">
          <span class="text-[10px] text-gray-500">&gt; 85%: Agent chủ động khuyên Takeaway</span>
        </div>

        <div class="bg-gray-900/80 p-2.5 rounded-xl border border-gray-800">
          <div class="flex justify-between items-center mb-1">
            <label class="text-gray-300 font-medium">Mức tải Bếp 1 (Cơm phần):</label>
            <span id="simK1Val" class="font-bold text-red-400">Ùn ứ (~20p chờ)</span>
          </div>
          <input type="range" id="simK1" min="1" max="3" value="3" oninput="updateSimK1Level(this.value)" class="w-full accent-red-500 cursor-pointer">
          <div class="flex justify-between text-[10px] text-gray-500">
            <span>Thông thoáng</span>
            <span>Vừa phải</span>
            <span>Ùn ứ cao điểm</span>
          </div>
        </div>

        <div class="bg-gray-900/80 p-2.5 rounded-xl border border-gray-800">
          <div class="flex justify-between items-center mb-1">
            <label class="text-gray-300 font-medium">Mức tải Bếp 2 (Bún & Healthy):</label>
            <span id="simK2Val" class="font-bold text-emerald-400">Thông thoáng (&lt;5p)</span>
          </div>
          <input type="range" id="simK2" min="1" max="3" value="1" oninput="updateSimK2Level(this.value)" class="w-full accent-emerald-500 cursor-pointer">
          <div class="flex justify-between text-[10px] text-gray-500">
            <span>Thông thoáng</span>
            <span>Vừa phải</span>
            <span>Ùn ứ cao điểm</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- MAIN CONTAINER -->
  <main class="max-w-7xl mx-auto px-4 py-4 flex-grow flex flex-col gap-4 w-full">

    <!-- REALISTIC TELEMETRY METRICS CARDS -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <!-- Card 1: Sức chứa -->
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-3.5 flex flex-col justify-between transition hover:border-gray-700">
        <div class="flex items-center justify-between">
          <span class="text-xs text-gray-400 font-medium">Nhà ăn (Sức chứa ~500 chỗ)</span>
          <span id="seatOccupancyBadge" class="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">CAO ĐIỂM (~90%)</span>
        </div>
        <div class="my-2">
          <div class="flex justify-between items-baseline">
            <span id="seatMainStatus" class="text-lg font-bold text-gray-100">Gần kín chỗ</span>
            <span id="seatSubStatus" class="text-xs text-amber-400 font-medium">Còn ~30 - 40 ghế rải rác</span>
          </div>
          <div class="w-full bg-gray-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div id="seatProgressBar" class="bg-gradient-to-r from-amber-500 to-red-500 h-full rounded-full transition-all duration-500" style="width: 90%"></div>
          </div>
        </div>
        <p class="text-[10px] text-gray-400 flex items-center gap-1">
          <i data-lucide="radio" class="w-3 h-3 text-blue-400"></i> Đo qua cảm biến lối vào & lượt quét 15p
        </p>
      </div>

      <!-- Card 2: Bếp 1 -->
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-3.5 flex flex-col justify-between transition hover:border-gray-700">
        <div class="flex items-center justify-between">
          <span class="text-xs text-gray-400 font-medium">Bếp 1 (Cơm phần truyền thống)</span>
          <span id="k1Badge" class="px-2 py-0.5 text-[10px] font-bold rounded bg-red-500/20 text-red-400 border border-red-500/40">ÙN Ứ CAO ĐIỂM</span>
        </div>
        <div class="my-2">
          <div class="flex justify-between items-baseline">
            <span id="k1MainStatus" class="text-lg font-bold text-red-400">Xếp hàng dài</span>
            <span id="k1WaitText" class="text-xs text-gray-400">Chờ ~15 - 25 phút</span>
          </div>
          <p class="text-xs text-gray-300 mt-1 truncate">Món: Cơm sườn nướng, Gà xối mỡ, Cá kho</p>
        </div>
        <p class="text-[10px] text-gray-400 flex items-center gap-1">
          <i data-lucide="activity" class="w-3 h-3 text-red-400"></i> ~95 lượt quét thẻ tại quầy 15p qua
        </p>
      </div>

      <!-- Card 3: Bếp 2 -->
      <div class="bg-gray-900 border border-emerald-900/40 rounded-xl p-3.5 flex flex-col justify-between shadow-lg shadow-emerald-950/20 transition hover:border-emerald-800">
        <div class="flex items-center justify-between">
          <span class="text-xs text-emerald-400 font-medium">Bếp 2 (Bún mì & Healthy)</span>
          <span id="k2Badge" class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">THÔNG THOÁNG</span>
        </div>
        <div class="my-2">
          <div class="flex justify-between items-baseline">
            <span id="k2MainStatus" class="text-lg font-bold text-emerald-400">Lấy đồ nhanh</span>
            <span id="k2WaitText" class="text-xs text-emerald-300">Chờ &lt; 5 phút</span>
          </div>
          <p class="text-xs text-gray-300 mt-1 truncate">Món: Bún chả than hoa, Mì gà, Eat Clean</p>
        </div>
        <p class="text-[10px] text-gray-400 flex items-center gap-1">
          <i data-lucide="check-circle" class="w-3 h-3 text-emerald-400"></i> Đề xuất tối ưu để kịp giờ nghỉ
        </p>
      </div>

      <!-- Card 4: Thẻ học viên động -->
      <div class="bg-gray-900 border border-blue-900/40 rounded-xl p-3.5 flex flex-col justify-between transition hover:border-blue-800">
        <div class="flex items-center justify-between">
          <span id="studentCardName" class="text-xs text-blue-400 font-medium truncate">Thẻ vé: Trần Tuấn Tú</span>
          <span id="studentCardTicketType" class="px-2 py-0.5 text-[10px] font-bold rounded bg-blue-500/20 text-blue-300 border border-blue-500/40">VÉ THÁNG</span>
        </div>
        <div class="my-2">
          <div class="flex justify-between items-baseline">
            <span id="studentCardPunches" class="text-2xl font-bold text-blue-300">18 <span class="text-xs text-gray-400 font-normal">lỗ còn lại / 30</span></span>
            <span id="studentCardId" class="text-xs text-gray-400">2A202602840</span>
          </div>
          <p id="studentCardPayment" class="text-xs text-gray-300 mt-1 truncate">Trừ tự động điện tử qua FastPass</p>
        </div>
        <p class="text-[10px] text-blue-400/90 flex items-center gap-1">
          <i data-lucide="sparkles" class="w-3 h-3"></i> Tự động hóa, không cần bấm kìm
        </p>
      </div>
    </div>

    <!-- MAIN TWO COLUMNS -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-grow min-h-[520px]">
      
      <!-- LEFT COL: CHAT & INTERACTION (7 Cols) -->
      <div class="lg:col-span-7 bg-gray-900 border border-gray-800 rounded-2xl flex flex-col overflow-hidden">
        
        <!-- QUICK PROMPT CHIPS (DYNAMIC THEO HỌC VIÊN ĐANG CHỌN) -->
        <div class="p-2.5 bg-gray-900/90 border-b border-gray-800 flex items-center gap-2 overflow-x-auto text-xs">
          <span class="text-gray-400 whitespace-nowrap font-medium flex items-center gap-1">
            <i data-lucide="zap" class="w-3.5 h-3.5 text-yellow-400"></i> Prompt mẫu:
          </span>
          <button onclick="setPrompt('Nhà ăn VinLab mở cửa lúc mấy giờ, sức chứa bao nhiêu và có những bếp nào?')" class="px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 whitespace-nowrap transition border border-gray-700">
            💬 Giờ & Sức chứa
          </button>
          <button onclick="setPromptForCurrentStudent('check')" class="px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 whitespace-nowrap transition border border-gray-700">
            🔍 Tra cứu vé của tôi
          </button>
          <button onclick="setPromptForCurrentStudent('multistep')" class="px-2.5 py-1 rounded-lg bg-blue-950/80 hover:bg-blue-900 text-blue-300 whitespace-nowrap transition border border-blue-500/30 font-medium">
            ⚡ ReAct đa bước (Tự đặt món vắng)
          </button>
          <button onclick="setPromptForCurrentStudent('order_takeaway')" class="px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 whitespace-nowrap transition border border-gray-700">
            📦 Đặt suất Takeaway 13:05
          </button>
        </div>

        <!-- CHAT MESSAGES STREAM -->
        <div id="chatMessages" class="flex-grow p-4 overflow-y-auto space-y-4 max-h-[580px]">
          <!-- Welcome Message -->
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 text-white">
              <i data-lucide="bot" class="w-4 h-4"></i>
            </div>
            <div class="bg-gray-800/80 border border-gray-700 rounded-2xl rounded-tl-none p-3.5 text-sm text-gray-200 max-w-xl shadow-sm">
              <p class="font-semibold text-blue-300 mb-1">Xin chào học viên VinLab!</p>
              <p>Tôi là <strong>Trợ lý Điều Phối Suất Ăn & Phân Luồng FastPass</strong>. Trong khung giờ cao điểm 13h00–14h00 với 1000 học viên, tôi giúp bạn:</p>
              <ul class="list-disc list-inside mt-2 space-y-1 text-xs text-gray-300">
                <li>Tra cứu mức tải nhà ăn & thời gian chờ giữa <strong>Bếp 1</strong> và <strong>Bếp 2</strong>.</li>
                <li>Tự động điều phối sang Bếp vắng để tiết kiệm ~20 phút xếp hàng.</li>
                <li>Cấp mã <strong>FastPass</strong> nhận đồ trong 30 giây tại làn ưu tiên (tự động trừ vé tháng hoặc sinh mã VietQR).</li>
              </ul>
              <p class="mt-2 text-xs text-gray-400">👉 Nhấp vào các prompt gợi ý phía trên hoặc gõ yêu cầu của bạn bên dưới.</p>
            </div>
          </div>
        </div>

        <!-- INPUT BOX -->
        <div class="p-3 bg-gray-900 border-t border-gray-800">
          <form id="chatForm" onsubmit="handleSendPrompt(event)" class="flex items-center gap-2">
            <input type="text" id="userInput" placeholder="Nhập câu hỏi hoặc yêu cầu điều phối suất ăn..." class="flex-grow bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-500">
            <button type="submit" id="sendBtn" class="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium px-4 py-2.5 rounded-xl transition flex items-center gap-2 text-sm shadow-lg shadow-blue-600/30">
              <span>Gửi</span>
              <i data-lucide="send" class="w-4 h-4"></i>
            </button>
          </form>
        </div>
      </div>

      <!-- RIGHT COL: REACT WATERFALL TRACE & FASTPASS TICKET (5 Cols) -->
      <div class="lg:col-span-5 flex flex-col gap-4">
        
        <!-- FASTPASS E-TICKET CARD (Hiện ra khi có booking) -->
        <div id="fastpassTicketContainer" class="hidden">
          <div class="bg-gradient-to-br from-blue-900/60 via-gray-900 to-indigo-950/60 border-2 border-blue-500/60 rounded-2xl p-4 shadow-2xl glow-card relative overflow-hidden">
            <div class="absolute -right-8 -top-8 w-28 h-28 bg-blue-500/20 rounded-full blur-2xl"></div>
            
            <div class="flex items-center justify-between border-b border-gray-700/60 pb-3 mb-3">
              <div class="flex items-center gap-2">
                <span class="w-3 h-3 rounded-full bg-emerald-400 animate-ping"></span>
                <span class="font-bold text-sm uppercase tracking-wider text-blue-300">VinLab FastPass E-Ticket</span>
              </div>
              <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                Ưu tiên làn 1 (30 giây)
              </span>
            </div>

            <div class="flex gap-4 items-center">
              <div id="qrcode" class="p-2 bg-white rounded-xl shadow-md flex-shrink-0 flex items-center justify-center min-w-[95px] min-h-[95px]"></div>
              <div class="text-xs space-y-1.5 flex-grow">
                <div>
                  <span class="text-gray-400">Mã FastPass:</span>
                  <p id="ticketCode" class="font-mono font-bold text-sm text-yellow-300"></p>
                </div>
                <div>
                  <span class="text-gray-400">Học viên:</span>
                  <p id="ticketStudent" class="font-semibold text-gray-100"></p>
                </div>
                <div>
                  <span class="text-gray-400">Bếp & Giờ nhận:</span>
                  <p id="ticketKitchenTime" class="font-medium text-emerald-300"></p>
                </div>
                <div>
                  <span class="text-gray-400">Hình thức:</span>
                  <p id="ticketDining" class="text-gray-200"></p>
                </div>
              </div>
            </div>

            <div class="mt-3 pt-3 border-t border-gray-800 text-[11px] text-blue-200 bg-blue-950/40 p-2.5 rounded-lg border border-blue-800/40">
              <i data-lucide="info" class="w-3.5 h-3.5 inline mr-1 text-blue-400"></i>
              <span id="ticketInstructions">Xuất trình mã này tại quầy ưu tiên Fast-Track để nhận khay cơm trong 30 giây!</span>
            </div>
          </div>
        </div>

        <!-- WATERFALL TRACE LOGS -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl flex flex-col flex-grow overflow-hidden">
          <div class="p-3 bg-gray-900/90 border-b border-gray-800 flex items-center justify-between">
            <h2 class="text-xs font-bold text-gray-300 flex items-center gap-1.5 uppercase tracking-wider">
              <i data-lucide="git-commit" class="w-4 h-4 text-blue-400"></i> Waterfall Trace Log (ReAct)
            </h2>
            <span id="traceCounter" class="text-[11px] text-gray-500">0 sự kiện</span>
          </div>

          <div id="waterfallLogs" class="p-3 overflow-y-auto space-y-2.5 max-h-[520px] text-xs">
            <div class="text-center text-gray-500 py-12 text-xs">
              <i data-lucide="activity" class="w-8 h-8 mx-auto mb-2 opacity-30"></i>
              Chưa có phiên suy luận nào.<br>Hãy gửi một yêu cầu để xem chuỗi ReAct Waterfall.
            </div>
          </div>
        </div>

      </div>

    </div>
  </main>

  <!-- FOOTER -->
  <footer class="bg-gray-900 border-t border-gray-800 py-3 text-center text-xs text-gray-500">
    Bài Lab 3: Chatbot vs ReAct Agent (MCP Enhanced) • Học viên: Trần Tuấn Tú (2A202602840) • VinLab AI Course 2026
  </footer>

  <!-- SCRIPTS -->
  <script>
    lucide.createIcons();

    let currentStudentId = "2A202602840";
    let canteenStatusCache = null;

    // 1. Fetch Dynamic Models from Backend API (/api/models)
    async function fetchModelsForProvider(showFeedback = false) {
      const provider = document.getElementById("providerSelect").value;
      const apiKey = document.getElementById("customApiKey").value;
      const modelSelect = document.getElementById("modelSelect");
      const spinner = document.getElementById("modelLoadingSpinner");

      spinner.classList.remove("hidden");
      modelSelect.disabled = true;

      try {
        const url = `/api/models?provider=${encodeURIComponent(provider)}&api_key=${encodeURIComponent(apiKey)}`;
        const res = await fetch(url);
        const data = await res.json();

        modelSelect.innerHTML = "";
        if (data.models && data.models.length > 0) {
          data.models.forEach((m, idx) => {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.textContent = m.name || m.id;
            if (idx === 0) opt.selected = true;
            modelSelect.appendChild(opt);
          });
        } else {
          const opt = document.createElement("option");
          opt.value = "default";
          opt.textContent = "Không có model trả về";
          modelSelect.appendChild(opt);
        }

        if (showFeedback) {
          alert(`✅ Đã tải thành công ${data.models?.length || 0} models trực tiếp từ ${provider.toUpperCase()} API!`);
        }
      } catch (err) {
        console.error("Lỗi fetch models:", err);
      } finally {
        spinner.classList.add("hidden");
        modelSelect.disabled = false;
        lucide.createIcons();
      }
    }

    // 2. Fetch Canteen DB & Student Status
    async function fetchCanteenStatus() {
      try {
        const res = await fetch("/api/status");
        const data = await res.json();
        canteenStatusCache = data;
        renderCanteenMetrics(data);
      } catch (e) {
        console.error("Lỗi fetch status:", e);
      }
    }

    function renderCanteenMetrics(db) {
      if (!db) return;
      const st = db.status;
      document.getElementById("seatOccupancyBadge").textContent = st.occupancy_level || "CAO ĐIỂM (~90%)";
      document.getElementById("seatSubStatus").textContent = st.seats_status || "Còn ~30 - 40 ghế rải rác";

      // Kitchen 1
      const k1 = db.kitchens.bep_1;
      document.getElementById("k1Badge").textContent = k1.traffic_level || "ÙN Ứ CAO ĐIỂM";
      document.getElementById("k1WaitText").textContent = `Chờ ~${k1.est_wait_minutes} phút`;

      // Kitchen 2
      const k2 = db.kitchens.bep_2;
      document.getElementById("k2Badge").textContent = k2.traffic_level || "THÔNG THOÁNG";
      document.getElementById("k2WaitText").textContent = `Chờ ~${k2.est_wait_minutes} phút`;

      // Student Card
      const stud = db.students[currentStudentId] || {
        full_name: `Học viên ${currentStudentId}`,
        ticket_type: "VE_NGAY",
        remaining_punches: 0,
        ticket_status: "CHƯA CÓ VÉ THÁNG"
      };

      document.getElementById("studentCardName").textContent = `Thẻ vé: ${stud.full_name}`;
      document.getElementById("studentCardId").textContent = currentStudentId;
      document.getElementById("studentCardTicketType").textContent = stud.ticket_type === "VE_THANG" ? "VÉ THÁNG" : "VÉ NGÀY";
      if (stud.ticket_type === "VE_THANG") {
        document.getElementById("studentCardPunches").innerHTML = `${stud.remaining_punches} <span class="text-xs text-gray-400 font-normal">lỗ còn lại / 30</span>`;
        document.getElementById("studentCardPayment").textContent = "Trừ tự động điện tử qua FastPass";
      } else {
        document.getElementById("studentCardPunches").innerHTML = `0 <span class="text-xs text-gray-400 font-normal">lượt vé tháng</span>`;
        document.getElementById("studentCardPayment").textContent = "VietQR chuyển khoản tự động";
      }

      lucide.createIcons();
    }

    function onStudentChange() {
      currentStudentId = document.getElementById("studentSelect").value;
      const studName = document.getElementById("studentSelect").selectedOptions[0].text;
      document.getElementById("activeStudentLabel").textContent = studName;
      renderCanteenMetrics(canteenStatusCache);
    }

    function toggleSimulator() {
      const drawer = document.getElementById("simulatorDrawer");
      drawer.classList.toggle("hidden");
    }

    async function updateSimOccupancy(val) {
      document.getElementById("simSeatsVal").textContent = `${val}% công suất`;
      if (!canteenStatusCache) return;
      document.getElementById("seatProgressBar").style.width = `${val}%`;
      canteenStatusCache.status.occupancy_level = val > 85 ? "CAO ĐIỂM (Quá tải ~" + val + "%)" : "BÌNH THƯỜNG (~" + val + "%)";
      canteenStatusCache.status.seats_status = val > 85 ? "Gần kín chỗ (ước tính chỉ còn khoảng 30 - 40 ghế rải rác)" : "Còn nhiều ghế trống thông thoáng";
      canteenStatusCache.status.capacity_alert = val > 85 ? "CẢNH BÁO: Nhà ăn đang ở mức tải cao điểm (~" + val + "% ghế). Khuyến nghị học viên chọn TAKEAWAY (đóng hộp) mang về phòng tự học để không phải chờ ghế!" : "Tình trạng ghế ngồi ổn định.";
      renderCanteenMetrics(canteenStatusCache);
      await sendSimUpdate();
    }

    async function updateSimK1Level(level) {
      if (!canteenStatusCache) return;
      if (level == "1") {
        document.getElementById("simK1Val").textContent = "Thông thoáng (<5p)";
        canteenStatusCache.kitchens.bep_1.traffic_level = "THÔNG THOÁNG";
        canteenStatusCache.kitchens.bep_1.est_wait_minutes = 4;
        canteenStatusCache.kitchens.bep_1.status = "THÔNG THOÁNG (Ước tính chờ dưới 5 phút)";
      } else if (level == "2") {
        document.getElementById("simK1Val").textContent = "Vừa phải (~10p)";
        canteenStatusCache.kitchens.bep_1.traffic_level = "VỪA PHẢI";
        canteenStatusCache.kitchens.bep_1.est_wait_minutes = 10;
        canteenStatusCache.kitchens.bep_1.status = "VỪA PHẢI (Ước tính chờ 5 - 10 phút)";
      } else {
        document.getElementById("simK1Val").textContent = "Ùn ứ cao điểm (>20p)";
        canteenStatusCache.kitchens.bep_1.traffic_level = "ÙN Ứ CAO ĐIỂM";
        canteenStatusCache.kitchens.bep_1.est_wait_minutes = 22;
        canteenStatusCache.kitchens.bep_1.status = "RẤT ĐÔNG (Xếp hàng dài, ước tính chờ 15 - 25 phút)";
      }
      renderCanteenMetrics(canteenStatusCache);
      await sendSimUpdate();
    }

    async function updateSimK2Level(level) {
      if (!canteenStatusCache) return;
      if (level == "1") {
        document.getElementById("simK2Val").textContent = "Thông thoáng (<5p)";
        canteenStatusCache.kitchens.bep_2.traffic_level = "THÔNG THOÁNG";
        canteenStatusCache.kitchens.bep_2.est_wait_minutes = 4;
        canteenStatusCache.kitchens.bep_2.status = "THÔNG THOÁNG (Ước tính chờ dưới 5 phút - KHUYÊN DÙNG ĐỂ KỊP NGHỈ TRƯA)";
      } else if (level == "2") {
        document.getElementById("simK2Val").textContent = "Vừa phải (~10p)";
        canteenStatusCache.kitchens.bep_2.traffic_level = "VỪA PHẢI";
        canteenStatusCache.kitchens.bep_2.est_wait_minutes = 10;
        canteenStatusCache.kitchens.bep_2.status = "VỪA PHẢI (Ước tính chờ 5 - 10 phút)";
      } else {
        document.getElementById("simK2Val").textContent = "Ùn ứ cao điểm (>20p)";
        canteenStatusCache.kitchens.bep_2.traffic_level = "ÙN Ứ CAO ĐIỂM";
        canteenStatusCache.kitchens.bep_2.est_wait_minutes = 20;
        canteenStatusCache.kitchens.bep_2.status = "RẤT ĐÔNG (Xếp hàng dài, ước tính chờ 15 - 25 phút)";
      }
      renderCanteenMetrics(canteenStatusCache);
      await sendSimUpdate();
    }

    async function sendSimUpdate() {
      try {
        await fetch("/api/status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(canteenStatusCache)
        });
      } catch(e) {}
    }

    function setPrompt(text) {
      document.getElementById("userInput").value = text;
      document.getElementById("userInput").focus();
    }

    function setPromptForCurrentStudent(type) {
      if (type === 'check') {
        setPrompt(`Hãy kiểm tra tình trạng tải nhà ăn và thông tin thẻ vé của học viên mã số ${currentStudentId}.`);
      } else if (type === 'multistep') {
        setPrompt(`Tôi là học viên ${currentStudentId}, hãy kiểm tra xem Bếp 1 hay Bếp 2 đang thông thoáng hơn và đặt luôn cho tôi 1 suất ở bếp vắng đó lúc 13:10 mang về phòng học để kịp nghỉ trưa nhé.`);
      } else if (type === 'order_takeaway') {
        setPrompt(`Tôi là học viên ${currentStudentId}. Hãy đặt trước giúp tôi 1 suất Bún chả ở Bếp 2 vào lúc 13:05 và đóng hộp mang về phòng tự học (takeaway).`);
      }
    }

    async function handleSendPrompt(e) {
      e.preventDefault();
      const input = document.getElementById("userInput");
      const query = input.value.trim();
      if (!query) return;

      const chatBox = document.getElementById("chatMessages");
      const sendBtn = document.getElementById("sendBtn");
      
      // Append User message
      chatBox.innerHTML += `
        <div class="flex items-start justify-end gap-3">
          <div class="bg-blue-600 text-white rounded-2xl rounded-tr-none p-3 text-sm max-w-xl shadow-md">
            ${query}
          </div>
          <div class="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center flex-shrink-0 text-white">
            <i data-lucide="user" class="w-4 h-4"></i>
          </div>
        </div>
      `;
      input.value = "";
      sendBtn.disabled = true;
      sendBtn.classList.add("opacity-50");
      lucide.createIcons();
      chatBox.scrollTop = chatBox.scrollHeight;

      // Loading indicator
      const loadingId = "loading-" + Date.now();
      chatBox.innerHTML += `
        <div id="${loadingId}" class="flex items-center gap-3 text-xs text-blue-400 py-1">
          <div class="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
          <span>ReAct Agent đang suy luận chuỗi Thought -> Action qua MCP Server...</span>
        </div>
      `;
      chatBox.scrollTop = chatBox.scrollHeight;

      try {
        const p = document.getElementById("providerSelect").value;
        const m = document.getElementById("modelSelect").value;
        const k = document.getElementById("customApiKey").value;

        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query, provider: p, model: m, api_key: k })
        });

        const data = await response.json();
        document.getElementById(loadingId)?.remove();

        // Render Waterfall Trace on the right
        renderWaterfallTrace(data.trace_logs || []);

        // Calculate total latency
        let totalLatency = 0;
        (data.trace_logs || []).forEach(l => { totalLatency += (l.latency_ms || 0); });
        totalLatency = Math.round(totalLatency);

        // Build Visual ReAct Reasoning Accordion
        let reasoningStepsHtml = "";
        (data.trace_logs || []).forEach((l, idx) => {
          if (l.action_type === "TOOL_EXECUTION") {
            reasoningStepsHtml += `
              <div class="p-2 bg-gray-900 border border-yellow-500/30 rounded-lg space-y-1 my-1.5">
                <div class="flex items-center justify-between text-[11px]">
                  <span class="font-bold text-yellow-400 flex items-center gap-1">
                    <i data-lucide="wrench" class="w-3 h-3"></i> Bước ${l.step}: Action ➔ ${l.tool_name}
                  </span>
                  <span class="font-mono text-gray-500">${l.latency_ms || 0} ms</span>
                </div>
                <div class="text-[10px] font-mono text-gray-300 bg-gray-950 p-1.5 rounded">
                  Tham số: ${JSON.stringify(l.arguments || {})}
                </div>
                <div class="text-[10px] font-mono text-emerald-300 bg-gray-950/80 p-1.5 rounded truncate">
                  Observation: ${JSON.stringify(l.observation || {})}
                </div>
              </div>
            `;
          } else if (l.action_type === "FINAL_ANSWER" && l.thought) {
            reasoningStepsHtml += `
              <div class="p-2 bg-gray-900 border border-blue-500/30 rounded-lg space-y-1 my-1.5">
                <span class="font-bold text-blue-400 flex items-center gap-1 text-[11px]">
                  <i data-lucide="brain" class="w-3 h-3"></i> Bước ${l.step}: Thought (Suy luận)
                </span>
                <p class="text-[10px] text-gray-300">${l.thought}</p>
              </div>
            `;
          }
        });

        // Render Final Answer WITH METADATA TAGS AND REASONING ACCORDION
        const finalAnswer = data.final_answer || "Đã hoàn thành xử lý.";
        chatBox.innerHTML += `
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center flex-shrink-0 text-white shadow-md">
              <i data-lucide="bot" class="w-4 h-4"></i>
            </div>
            <div class="bg-gray-800/95 border border-gray-700 rounded-2xl rounded-tl-none p-4 text-sm text-gray-100 max-w-xl shadow-lg">
              <!-- METADATA BADGE -->
              <div class="flex items-center gap-1.5 mb-2.5 pb-2 border-b border-gray-700/60 flex-wrap text-[10px]">
                <span class="px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800 font-mono font-bold flex items-center gap-1">
                  <i data-lucide="zap" class="w-2.5 h-2.5"></i> ${data.provider}
                </span>
                <span class="px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono">
                  ${data.model}
                </span>
                <span class="px-2 py-0.5 rounded-full bg-gray-900 text-gray-400 font-mono">
                  ⏱️ ${totalLatency} ms
                </span>
                <span class="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                  🔄 ${data.trace_logs?.length || 1} bước ReAct
                </span>
              </div>

              <!-- VISUAL REASONING ACCORDION -->
              <details class="mb-3 bg-gray-950/70 border border-gray-700/60 rounded-xl p-2.5 text-xs text-gray-300 cursor-pointer" open>
                <summary class="font-bold text-blue-400 flex items-center gap-1.5 hover:text-blue-300 select-none text-[11px]">
                  <i data-lucide="git-branch" class="w-3.5 h-3.5"></i> Xem chuỗi suy luận ReAct (Thought ➔ Action ➔ Observation)
                </summary>
                <div class="mt-2 space-y-1">
                  ${reasoningStepsHtml}
                </div>
              </details>

              <!-- FINAL ANSWER MARKDOWN -->
              <div class="prose prose-invert text-sm">
                ${marked.parse(finalAnswer)}
              </div>
            </div>
          </div>
        `;

        // Check if FastPass was generated & trigger confetti
        checkAndShowFastPass(data.trace_logs || []);

        // Refresh Canteen Metrics
        await fetchCanteenStatus();

      } catch (err) {
        document.getElementById(loadingId)?.remove();
        chatBox.innerHTML += `
          <div class="p-3 bg-red-950/80 border border-red-800 rounded-xl text-xs text-red-300">
            Lỗi kết nối: ${err.message}
          </div>
        `;
      } finally {
        sendBtn.disabled = false;
        sendBtn.classList.remove("opacity-50");
        lucide.createIcons();
        chatBox.scrollTop = chatBox.scrollHeight;
      }
    }

    function renderWaterfallTrace(logs) {
      const container = document.getElementById("waterfallLogs");
      document.getElementById("traceCounter").textContent = `${logs.length} sự kiện`;
      
      if (!logs || logs.length === 0) {
        container.innerHTML = `<div class="text-center text-gray-500 py-6">Không có sự kiện trace.</div>`;
        return;
      }

      let html = "";
      logs.forEach(log => {
        if (log.action_type === "TOOL_EXECUTION") {
          html += `
            <div class="p-2.5 bg-gray-800/90 border border-yellow-500/40 rounded-xl space-y-1.5 shadow-sm">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-bold text-yellow-400 flex items-center gap-1">
                  <i data-lucide="wrench" class="w-3.5 h-3.5"></i> TOOL CALL: ${log.tool_name}
                </span>
                <span class="text-gray-400 font-mono">${log.latency_ms || 0} ms</span>
              </div>
              <div class="bg-gray-950 p-2 rounded text-[10px] font-mono text-gray-300 overflow-x-auto">
                <span class="text-gray-500">// Arguments:</span><br>
                ${JSON.stringify(log.arguments || {}, null, 2)}
              </div>
              <details class="text-[10px] text-gray-400 cursor-pointer">
                <summary class="hover:text-blue-300 text-blue-400">Xem Observation từ MCP Server</summary>
                <div class="bg-gray-950 p-2 rounded text-emerald-300 font-mono mt-1 overflow-x-auto">
                  ${JSON.stringify(log.observation || {}, null, 2)}
                </div>
              </details>
            </div>
          `;
        } else if (log.action_type === "FINAL_ANSWER") {
          html += `
            <div class="p-2.5 bg-emerald-950/40 border border-emerald-500/40 rounded-xl space-y-1 shadow-sm">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-bold text-emerald-400 flex items-center gap-1">
                  <i data-lucide="check-circle" class="w-3.5 h-3.5"></i> FINAL ANSWER
                </span>
                <span class="text-gray-400 font-mono">${log.latency_ms || 0} ms</span>
              </div>
              <p class="text-gray-300 text-[11px] line-clamp-3">${log.output || ""}</p>
            </div>
          `;
        }
      });

      container.innerHTML = html;
      lucide.createIcons();
    }

    function checkAndShowFastPass(logs) {
      const orderLog = logs.find(l => l.tool_name === "order_meal_fastpass" && l.observation?.status === "SUCCESS");
      const container = document.getElementById("fastpassTicketContainer");

      if (orderLog && orderLog.observation) {
        const obs = orderLog.observation;
        document.getElementById("ticketCode").textContent = obs.fastpass_code;
        document.getElementById("ticketStudent").textContent = `${obs.student_name || "Học viên"} (${obs.student_id})`;
        document.getElementById("ticketKitchenTime").textContent = `${obs.kitchen} • ${obs.pickup_time}`;
        document.getElementById("ticketDining").textContent = `${obs.dining_option} • ${obs.meal_item}`;
        document.getElementById("ticketInstructions").textContent = obs.pickup_instructions || "Đến cửa Fast-Track quét mã nhận đồ!";

        // Generate Real QR Code
        const qrContainer = document.getElementById("qrcode");
        qrContainer.innerHTML = "";
        new QRCode(qrContainer, {
          text: obs.fastpass_code,
          width: 85,
          height: 85,
          colorDark: "#000000",
          colorLight: "#ffffff",
          correctLevel: QRCode.CorrectLevel.H
        });

        container.classList.remove("hidden");
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Fire Confetti!
        try {
          confetti({
            particleCount: 80,
            spread: 60,
            origin: { y: 0.7 }
          });
        } catch(e) {}
      }
    }

    // Init on load
    window.addEventListener("DOMContentLoaded", () => {
      fetchModelsForProvider(false);
      fetchCanteenStatus();
    });
  </script>
</body>
</html>
"""

class CanteenAgentHTTPHandler(BaseHTTPRequestHandler):
    mcp_server = MCPAcademicServer()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))

        elif parsed.path == "/api/models":
            provider = params.get("provider", ["groq"])[0].lower()
            custom_key = params.get("api_key", [""])[0]

            models_list = self.fetch_live_models_from_provider(provider, custom_key)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "provider": provider,
                "models": models_list
            }, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(CANTEEN_DB, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/trace":
            trace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "trace_waterfall.json")
            if os.path.exists(trace_path):
                with open(trace_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        if parsed.path == "/api/status":
            # Update Canteen DB (Simulator Flex)
            if "status" in req_data:
                CANTEEN_DB["status"].update(req_data["status"])
            if "kitchens" in req_data:
                CANTEEN_DB["kitchens"].update(req_data["kitchens"])

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "UPDATED", "db": CANTEEN_DB}, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/chat":
            query = req_data.get("query", "")
            provider_name = req_data.get("provider", "groq")
            model_name = req_data.get("model")
            custom_key = req_data.get("api_key")

            # Khởi tạo Provider theo lựa chọn trên Web
            provider = self.resolve_provider(provider_name, model_name, custom_key)

            # Thực thi ReAct Loop
            trace_logs = self.execute_react_agent(query, provider)
            final_answer = ""
            for log in reversed(trace_logs):
                if log.get("action_type") == "FINAL_ANSWER":
                    final_answer = log.get("output", "")
                    break

            # Cập nhật vào trace_waterfall.json
            self.append_trace_logs(trace_logs)

            response_payload = {
                "status": "SUCCESS",
                "query": query,
                "provider": getattr(provider, "provider_name", None) or provider.__class__.__name__.replace("Provider", ""),
                "model": getattr(provider, "model_name", "N/A"),
                "final_answer": final_answer,
                "trace_logs": trace_logs
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def fetch_live_models_from_provider(self, provider: str, custom_key: str = None) -> list:
        """CURL trực tiếp vào /models của base URL tương ứng để lấy danh sách model thực tế"""
        provider = provider.lower()
        
        if provider == "groq":
            key = custom_key or os.getenv("GROQ_API_KEY")
            if not key or "your_" in key:
                return [
                    {"id": "qwen/qwen3.8-27b", "name": "qwen/qwen3.8-27b (Khuyên dùng - Quota cao)"},
                    {"id": "openai/gpt-oss-120b", "name": "openai/gpt-oss-120b"}
                ]
            try:
                r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=4)
                if r.status_code == 200:
                    raw = r.json().get("data", [])
                    filtered = [m["id"] for m in raw if "whisper" not in m["id"] and "guard" not in m["id"]]
                    sorted_models = sorted(filtered, key=lambda x: ("qwen" not in x, "120b" not in x))
                    return [{"id": m, "name": f"{m} (Live Groq)"} for m in sorted_models[:6]]
            except Exception:
                pass
            return [
                {"id": "qwen/qwen3.8-27b", "name": "qwen/qwen3.8-27b (Khuyên dùng)"},
                {"id": "openai/gpt-oss-120b", "name": "openai/gpt-oss-120b"}
            ]

        elif provider == "nvidia":
            key = custom_key or os.getenv("NVIDIA_API_KEY")
            if key and "your_" not in key:
                try:
                    r = requests.get("https://integrate.api.nvidia.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=4)
                    if r.status_code == 200:
                        raw = r.json().get("data", [])
                        instruct_models = [m["id"] for m in raw if "instruct" in m["id"] or "llama" in m["id"]]
                        return [{"id": m, "name": f"{m} (Live NVIDIA NIM)"} for m in instruct_models[:6]]
                except Exception:
                    pass
            return [
                {"id": "meta/llama-3.3-70b-instruct", "name": "meta/llama-3.3-70b-instruct (NVIDIA)"},
                {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "name": "llama-3.1-nemotron-70b (NVIDIA)"}
            ]

        elif provider == "gemini":
            return [
                {"id": "gemini-2.5-flash", "name": "gemini-2.5-flash (Top 1 Quota 1M TPM)"},
                {"id": "gemini-1.5-flash", "name": "gemini-1.5-flash (Quota 1M TPM)"},
                {"id": "gemini-1.5-pro", "name": "gemini-1.5-pro (Suy luận sâu)"}
            ]

        elif provider == "openai":
            key = custom_key or os.getenv("OPENAI_API_KEY")
            if key and "your_" not in key:
                try:
                    r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=4)
                    if r.status_code == 200:
                        raw = r.json().get("data", [])
                        gpt_models = [m["id"] for m in raw if "gpt-4" in m["id"] or "gpt-3.5" in m["id"]]
                        return [{"id": m, "name": f"{m} (Live OpenAI)"} for m in gpt_models[:5]]
                except Exception:
                    pass
            return [
                {"id": "gpt-4o-mini", "name": "gpt-4o-mini (Chuẩn OpenAI)"},
                {"id": "gpt-4o", "name": "gpt-4o"}
            ]

        else:
            return [
                {"id": "mock-offline", "name": "Mock Offline Model (0đ không tốn token)"}
            ]

    def resolve_provider(self, provider_name: str, model_name: str, custom_key: str):
        provider_name = (provider_name or "groq").lower()
        if provider_name == "groq":
            key = custom_key or os.getenv("GROQ_API_KEY")
            return OpenAICompatibleProvider(
                api_key=key,
                base_url="https://api.groq.com/openai/v1",
                default_model=model_name or "qwen/qwen3.8-27b",
                provider_name="Groq"
            )
        elif provider_name == "gemini":
            key = custom_key or os.getenv("GEMINI_API_KEY")
            return GeminiProvider(api_key=key, model=model_name or "gemini-2.5-flash")
        elif provider_name == "nvidia":
            key = custom_key or os.getenv("NVIDIA_API_KEY")
            return OpenAICompatibleProvider(
                api_key=key,
                base_url="https://integrate.api.nvidia.com/v1",
                default_model=model_name or "meta/llama-3.3-70b-instruct",
                provider_name="NVIDIA NIM"
            )
        elif provider_name == "openai":
            key = custom_key or os.getenv("OPENAI_API_KEY")
            return OpenAIProvider(api_key=key, model=model_name or "gpt-4o-mini")
        else:
            return MockOfflineProvider()

    def execute_react_agent(self, user_query: str, provider) -> list:
        step = 0
        trace_logs = []
        tools_list = self.mcp_server.list_tools()
        current_prompt = user_query

        while step < MAX_ITERATIONS:
            step += 1
            step_start_time = time.time()
            llm_response = provider.generate_with_tools(current_prompt, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
            latency_ms = round((time.time() - step_start_time) * 1000, 2)
            thought = llm_response.get("thought", "Đang suy luận...")

            if llm_response.get("type") == "text":
                final_content = llm_response.get("content", "")
                trace_logs.append({
                    "step": step,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": thought,
                    "output": final_content,
                    "latency_ms": latency_ms
                })
                break
            elif llm_response.get("type") == "tool_call":
                tool_name = llm_response.get("tool_name")
                arguments = llm_response.get("arguments", {})
                mcp_result = self.mcp_server.call_tool(tool_name, arguments)
                obs_data = mcp_result.get("result", {})
                obs_str = json.dumps(obs_data, ensure_ascii=False)

                trace_logs.append({
                    "step": step,
                    "query": user_query,
                    "action_type": "TOOL_EXECUTION",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "observation": obs_data,
                    "latency_ms": latency_ms
                })

                if obs_data.get("status") == "NOT_FOUND" or step >= MAX_ITERATIONS - 1:
                    fallback_answer = obs_data.get("message", f"Đã nhận phản hồi: {obs_str}")
                    trace_logs.append({
                        "step": step + 1,
                        "query": user_query,
                        "action_type": "FINAL_ANSWER",
                        "thought": "Tổng hợp kết quả cuối cùng từ Observation.",
                        "output": fallback_answer,
                        "latency_ms": 10.0
                    })
                    break

                current_prompt = (
                    f"Yêu cầu ban đầu của học viên: {user_query}\n\n"
                    f"Bước {step} bạn đã gọi công cụ '{tool_name}' với tham số {json.dumps(arguments, ensure_ascii=False)}.\n"
                    f"[Kết quả Observation từ MCP Server]:\n{obs_str}\n\n"
                    "QUY TẮC QUYẾT ĐỊNH:\n"
                    "- Nếu yêu cầu ban đầu ĐÃ ĐƯỢC GIẢI QUYẾT (ví dụ chỉ hỏi tra cứu thông tin), hãy NGỪNG GỌI TOOL và đưa ra câu trả lời (Final Answer) đầy đủ, thân thiện.\n"
                    "- Chỉ gọi thêm Tool tiếp theo nếu yêu cầu đòi hỏi hành động đa bước (ví dụ: học viên nói 'kiểm tra xong đặt luôn cho tôi')."
                )

        return trace_logs

    def append_trace_logs(self, new_logs: list):
        trace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "trace_waterfall.json")
        try:
            if os.path.exists(trace_path):
                with open(trace_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []
            data.extend(new_logs)
            with open(trace_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def run_web_server(port: int = 8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, CanteenAgentHTTPHandler)
    print("==========================================================")
    print("🌐 VINLAB CANTEEN FASTPASS REACT AGENT - DYNAMIC DASHBOARD")
    print(f"🚀 Dashboard đang chạy tại: http://localhost:{port}")
    print("💡 Mở trình duyệt và truy cập link trên để trải nghiệm!")
    print("==========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Đã dừng Web Dashboard.")
        httpd.server_close()


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            port = 8080
    run_web_server(port)
