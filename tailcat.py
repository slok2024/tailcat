import os
import sys
import json
import re
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

class TailcatGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Tailcat GUI 控制面板")
        self.geometry("900x680")
        self.minsize(800, 600)

        # 核心进程句柄
        self.server_process = None

        # 界面初始化
        self._init_styles()
        self._create_top_path_bar()
        self._create_notebook()
        
        # 退出时清理子进程
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", padding=[12, 6], font=('Segoe UI', 9, 'bold'))
        style.configure("Header.TLabel", font=('Segoe UI', 10, 'bold'))

    def _create_top_path_bar(self):
        """顶部程序可执行文件路径配置"""
        frame = ttk.LabelFrame(self, text=" Tailcat 可执行文件路径 ", padding=8)
        frame.pack(fill=tk.X, padx=10, pady=5)

        default_path = r"D:\内核编译\tailcat-0.7.0\tailcat.exe"
        if not os.path.exists(default_path):
            default_path = "tailcat.exe"

        self.exe_path_var = tk.StringVar(value=default_path)
        
        entry = ttk.Entry(frame, textvariable=self.exe_path_var, font=('Consolas', 9))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        btn_browse = ttk.Button(frame, text="浏览...", command=self.browse_exe)
        btn_browse.pack(side=tk.RIGHT)

    def browse_exe(self):
        path = filedialog.askopenfilename(
            title="选择 tailcat.exe",
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")]
        )
        if path:
            self.exe_path_var.set(path)

    def _create_notebook(self):
        """选项卡容器"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 各功能页面
        self.tab_server = ttk.Frame(self.notebook)
        self.tab_client = ttk.Frame(self.notebook)
        self.tab_keys = ttk.Frame(self.notebook)
        self.tab_tools = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_server, text=" 🚀 服务端 (Serve/Recv) ")
        self.notebook.add(self.tab_client, text=" 🔗 客户端 (Socks/SSH/CP/Forward) ")
        self.notebook.add(self.tab_keys, text=" 🔑 密钥管理 (Genkey) ")
        self.notebook.add(self.tab_tools, text=" 🛠️ 诊断与工具 (Ping/Parse/Resolve) ")

        self._build_server_tab()
        self._build_client_tab()
        self._build_keys_tab()
        self._build_tools_tab()

    # =========================================================================
    # 1. 服务端 Tab
    # =========================================================================
    def _build_server_tab(self):
        # 服务端生成地址展示与复制区域
        addr_frame = ttk.LabelFrame(self.tab_server, text=" 服务端连接地址 ", padding=8)
        addr_frame.pack(fill=tk.X, padx=10, pady=(5, 0))

        self.server_address_var = tk.StringVar(value="等待服务端启动生成地址...")
        # 修复位置：将 font=('Consolas', 9.5, 'bold') 修改为 10（整数字号）
        self.server_address_entry = ttk.Entry(
            addr_frame, 
            textvariable=self.server_address_var, 
            state="readonly", 
            font=('Consolas', 10, 'bold')
        )
        self.server_address_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.btn_copy_address = ttk.Button(
            addr_frame, 
            text="复制地址", 
            state=tk.DISABLED, 
            command=self.copy_server_address
        )
        self.btn_copy_address.pack(side=tk.RIGHT)

        # 参数配置区域
        cfg_frame = ttk.LabelFrame(self.tab_server, text=" 服务端运行配置 ", padding=10)
        cfg_frame.pack(fill=tk.X, padx=10, pady=5)

        # 模式选择
        ttk.Label(cfg_frame, text="运行模式:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.server_mode_var = tk.StringVar(value="serve")
        mode_cb = ttk.Combobox(cfg_frame, textvariable=self.server_mode_var, state="readonly", 
                               values=["serve (通用服务)", "recv (只写文件接收箱)"])
        mode_cb.grid(row=0, column=1, columnspan=2, sticky=tk.EW, pady=2)

        # Serve 参数
        ttk.Label(cfg_frame, text="服务列表 (--serve):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.serve_args_var = tk.StringVar(value="80,443,no-auth-ssh")
        ttk.Entry(cfg_frame, textvariable=self.serve_args_var).grid(row=1, column=1, columnspan=2, sticky=tk.EW, pady=2)
        ttk.Label(cfg_frame, text="提示: 例如 22,80,8000-8999 或 all / exit-node / no-auth-ssh / files", 
                  font=('Segoe UI', 8), foreground="gray").grid(row=2, column=1, columnspan=2, sticky=tk.W)

        # Recv 路径
        ttk.Label(cfg_frame, text="接收目录 (Recv 模式):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.recv_dir_var = tk.StringVar(value=os.path.expanduser("~/inbox"))
        ttk.Entry(cfg_frame, textvariable=self.recv_dir_var).grid(row=3, column=1, sticky=tk.EW, pady=2)
        ttk.Button(cfg_frame, text="选择...", command=self.browse_recv_dir).grid(row=3, column=2, padx=(5, 0))

        # 密钥 & 附加参数
        ttk.Label(cfg_frame, text="使用密钥 (--key):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.server_key_var = tk.StringVar(value="default")
        ttk.Entry(cfg_frame, textvariable=self.server_key_var).grid(row=4, column=1, columnspan=2, sticky=tk.EW, pady=2)

        self.server_verbose_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg_frame, text="详细日志 (--verbose)", variable=self.server_verbose_var).grid(row=5, column=1, sticky=tk.W, pady=2)

        cfg_frame.columnconfigure(1, weight=1)

        # 控制按钮
        btn_frame = ttk.Frame(self.tab_server, padding=5)
        btn_frame.pack(fill=tk.X, padx=10)

        self.btn_start_server = ttk.Button(btn_frame, text=" ▶ 启动服务端 ", command=self.start_server)
        self.btn_start_server.pack(side=tk.LEFT, padx=5)

        self.btn_stop_server = ttk.Button(btn_frame, text=" ⏹ 停止服务端 ", command=self.stop_server, state=tk.DISABLED)
        self.btn_stop_server.pack(side=tk.LEFT, padx=5)

        # 控制台输出
        log_frame = ttk.LabelFrame(self.tab_server, text=" 实时运行日志 ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.server_log = scrolledtext.ScrolledText(log_frame, font=('Consolas', 9), bg="#1e1e1e", fg="#d4d4d4")
        self.server_log.pack(fill=tk.BOTH, expand=True)

    def copy_server_address(self):
        addr = self.server_address_var.get()
        if addr and not addr.startswith("等待"):
            self.clipboard_clear()
            self.clipboard_append(addr)
            messagebox.showinfo("成功", "服务端连接地址已复制到剪贴板！")

    def browse_recv_dir(self):
        d = filedialog.askdirectory(title="选择文件接收存放目录")
        if d:
            self.recv_dir_var.set(d)

    def start_server(self):
        exe = self.exe_path_var.get()
        if not os.path.exists(exe):
            messagebox.showerror("错误", f"找不到可执行文件: {exe}")
            return

        # 自动确保 AppData 路径下的 tailcat/keys 目录存在，防止 open keys 报错
        appdata = os.getenv('APPDATA')
        if appdata:
            keys_dir = os.path.join(appdata, "tailcat", "keys")
            os.makedirs(keys_dir, exist_ok=True)

        mode = self.server_mode_var.get()
        cmd = [exe]

        if self.server_verbose_var.get():
            cmd.append("--verbose")
        
        key = self.server_key_var.get().strip()
        if key:
            cmd.extend(["--key", key])

        if "recv" in mode:
            recv_dir = self.recv_dir_var.get().strip()
            if not recv_dir:
                messagebox.showwarning("警告", "请输入或选择接收目录！")
                return
            cmd.extend(["recv", recv_dir])
        else:
            serve_args = self.serve_args_var.get().strip()
            cmd.append("serve")
            if serve_args:
                cmd.append(serve_args)

        self.server_log.insert(tk.END, f"\n[GUI] 执行命令: {' '.join(cmd)}\n")
        self.server_log.see(tk.END)

        # 重置顶部地址显示状态
        self.server_address_var.set("正在启动并获取地址...")
        self.btn_copy_address.config(state=tk.DISABLED)

        def run():
            # 正则匹配 Server listening 后的 tcp... 地址
            key_pattern = re.compile(r"Server listening.*:\s*(tcp[A-Za-z0-9_-]+)")
            try:
                # 指定 encoding='utf-8' 与 errors='replace' 以避免控制台解码报错
                self.server_process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1, 
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                self.btn_start_server.config(state=tk.DISABLED)
                self.btn_stop_server.config(state=tk.NORMAL)

                for line in iter(self.server_process.stdout.readline, ''):
                    self.server_log.insert(tk.END, line)
                    self.server_log.see(tk.END)

                    # 捕获生成的 tcp 地址并更新顶部 UI
                    match = key_pattern.search(line)
                    if match:
                        tcp_addr = match.group(1)
                        self.after(0, lambda a=tcp_addr: [
                            self.server_address_var.set(a),
                            self.btn_copy_address.config(state=tk.NORMAL)
                        ])

                self.server_process.wait()
            except Exception as e:
                self.server_log.insert(tk.END, f"\n[ERROR] 启动失败: {str(e)}\n")
            finally:
                self.server_log.insert(tk.END, "\n[GUI] 服务端已停止。\n")
                self.btn_start_server.config(state=tk.NORMAL)
                self.btn_stop_server.config(state=tk.DISABLED)
                self.server_process = None

        threading.Thread(target=run, daemon=True).start()

    def stop_server(self):
        if self.server_process:
            self.server_process.terminate()

    # =========================================================================
    # 2. 客户端 Tab
    # =========================================================================
    def _build_client_tab(self):
        client_nb = ttk.Notebook(self.tab_client)
        client_nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Sub-tabs for client modes
        f_socks = ttk.Frame(client_nb)
        f_ssh = ttk.Frame(client_nb)
        f_cp = ttk.Frame(client_nb)
        f_fwd = ttk.Frame(client_nb)

        client_nb.add(f_socks, text=" SOCKS5 代理 ")
        client_nb.add(f_ssh, text=" SSH 连接 ")
        client_nb.add(f_cp, text=" 文件传输 (CP/LS) ")
        client_nb.add(f_fwd, text=" 端口转发 (Forward) ")

        # --- SOCKS5 ---
        ttk.Label(f_socks, text="Tailcat 地址 (<tc-addr>):").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.socks_addr_var = tk.StringVar()
        ttk.Entry(f_socks, textvariable=self.socks_addr_var, width=50).grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(f_socks, text="本地监听地址 (--listen):").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.socks_listen_var = tk.StringVar(value="127.0.0.1:1080")
        ttk.Entry(f_socks, textvariable=self.socks_listen_var).grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)

        btn_socks = ttk.Button(f_socks, text="开启 SOCKS5 代理", command=self.run_socks)
        btn_socks.grid(row=2, column=1, sticky=tk.W, padx=10, pady=10)

        f_socks.columnconfigure(1, weight=1)

        # --- SSH ---
        ttk.Label(f_ssh, text="目标地址 ([user@]<tc-addr>):").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.ssh_target_var = tk.StringVar()
        ttk.Entry(f_ssh, textvariable=self.ssh_target_var, width=50).grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(f_ssh, text="远程执行命令 (可选):").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.ssh_cmd_var = tk.StringVar()
        ttk.Entry(f_ssh, textvariable=self.ssh_cmd_var).grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)

        btn_ssh = ttk.Button(f_ssh, text="在系统终端中打开 SSH", command=self.run_ssh)
        btn_ssh.grid(row=2, column=1, sticky=tk.W, padx=10, pady=10)

        f_ssh.columnconfigure(1, weight=1)

        # --- CP / LS ---
        ttk.Label(f_cp, text="操作类型:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.cp_action_var = tk.StringVar(value="cp")
        rb_cp = ttk.Radiobutton(f_cp, text="拷贝文件 (cp)", variable=self.cp_action_var, value="cp")
        rb_ls = ttk.Radiobutton(f_cp, text="列出目录文件 (ls)", variable=self.cp_action_var, value="ls")
        rb_cp.grid(row=0, column=1, sticky=tk.W, padx=5)
        rb_ls.grid(row=0, column=1, sticky=tk.W, padx=120)

        ttk.Label(f_cp, text="源路径 (Source):").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.cp_src_var = tk.StringVar()
        ttk.Entry(f_cp, textvariable=self.cp_src_var).grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)
        ttk.Label(f_cp, text="例: local.txt 或 <tc-addr>:remote.txt", font=('Segoe UI', 8), foreground="gray").grid(row=2, column=1, sticky=tk.W, padx=10)

        ttk.Label(f_cp, text="目标路径 (Dest):").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.cp_dst_var = tk.StringVar()
        ttk.Entry(f_cp, textvariable=self.cp_dst_var).grid(row=3, column=1, sticky=tk.EW, padx=10, pady=5)

        btn_cp_exec = ttk.Button(f_cp, text="执行传输 / 列出", command=self.run_cp_ls)
        btn_cp_exec.grid(row=4, column=1, sticky=tk.W, padx=10, pady=10)

        f_cp.columnconfigure(1, weight=1)

        # --- Forward ---
        ttk.Label(f_fwd, text="Tailcat 地址 (<tc-addr>):").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.fwd_addr_var = tk.StringVar()
        ttk.Entry(f_fwd, textvariable=self.fwd_addr_var).grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(f_fwd, text="端口映射规则 ([local:]remote):").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.fwd_rule_var = tk.StringVar(value="8080:80")
        ttk.Entry(f_fwd, textvariable=self.fwd_rule_var).grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)
        ttk.Label(f_fwd, text="例: 8080:80 (将本地8080转发至远程80端口)", font=('Segoe UI', 8), foreground="gray").grid(row=2, column=1, sticky=tk.W, padx=10)

        btn_fwd = ttk.Button(f_fwd, text="开启端口转发", command=self.run_forward)
        btn_fwd.grid(row=3, column=1, sticky=tk.W, padx=10, pady=10)

        f_fwd.columnconfigure(1, weight=1)

        # 客户端通用日志显示区
        log_frame = ttk.LabelFrame(self.tab_client, text=" 客户端输出日志 ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.client_log = scrolledtext.ScrolledText(log_frame, font=('Consolas', 9), bg="#1e1e1e", fg="#d4d4d4", height=10)
        self.client_log.pack(fill=tk.BOTH, expand=True)

    def run_cmd_async(self, cmd_list, log_widget):
        def task():
            log_widget.insert(tk.END, f"\n[EXEC] {' '.join(cmd_list)}\n")
            log_widget.see(tk.END)
            try:
                p = subprocess.Popen(
                    cmd_list, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True, 
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                for line in iter(p.stdout.readline, ''):
                    log_widget.insert(tk.END, line)
                    log_widget.see(tk.END)
                p.wait()
            except Exception as e:
                log_widget.insert(tk.END, f"[ERROR] {str(e)}\n")
        threading.Thread(target=task, daemon=True).start()

    def run_socks(self):
        exe = self.exe_path_var.get()
        cmd = [exe, "socks"]
        listen = self.socks_listen_var.get().strip()
        if listen:
            cmd.append(f"--listen={listen}")
        addr = self.socks_addr_var.get().strip()
        if addr:
            cmd.append(addr)
        self.run_cmd_async(cmd, self.client_log)

    def run_ssh(self):
        exe = self.exe_path_var.get()
        target = self.ssh_target_var.get().strip()
        if not target:
            messagebox.showwarning("提示", "请输入目标 SSH 地址！")
            return
        cmd = [exe, "ssh", target]
        c = self.ssh_cmd_var.get().strip()
        if c:
            cmd.append(c)
        
        # 打开新的 cmd 窗口以交互方式使用 SSH
        full_cmd = f'start cmd /k "{exe} ssh {target} {c}"'
        os.system(full_cmd)

    def run_cp_ls(self):
        exe = self.exe_path_var.get()
        action = self.cp_action_var.get()
        if action == "ls":
            src = self.cp_src_var.get().strip()
            cmd = [exe, "ls", "-l", src]
        else:
            src = self.cp_src_var.get().strip()
            dst = self.cp_dst_var.get().strip()
            if not src or not dst:
                messagebox.showwarning("提示", "拷贝模式下必须填写源路径和目标路径！")
                return
            cmd = [exe, "cp", src, dst]
        self.run_cmd_async(cmd, self.client_log)

    def run_forward(self):
        exe = self.exe_path_var.get()
        addr = self.fwd_addr_var.get().strip()
        rule = self.fwd_rule_var.get().strip()
        if not addr or not rule:
            messagebox.showwarning("提示", "请填写 Tailcat 地址和映射规则！")
            return
        cmd = [exe, "forward", addr, rule]
        self.run_cmd_async(cmd, self.client_log)

    # =========================================================================
    # 3. 密钥管理 Tab
    # =========================================================================
    def _build_keys_tab(self):
        btn_frame = ttk.Frame(self.tab_keys, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="刷新/列出已有密钥 (genkey --list)", command=self.list_keys).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="获取当前公钥 (printpub)", command=self.print_pubkey).pack(side=tk.LEFT, padx=5)

        # 生成密钥区域
        gen_frame = ttk.LabelFrame(self.tab_keys, text=" 生成新密钥 ", padding=10)
        gen_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(gen_frame, text="密钥名称:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.key_name_var = tk.StringVar(value="default")
        ttk.Entry(gen_frame, textvariable=self.key_name_var).grid(row=0, column=1, sticky=tk.EW, pady=2, padx=5)

        self.key_is_client_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(gen_frame, text="客户端密钥 (--client)", variable=self.key_is_client_var).grid(row=0, column=2, sticky=tk.W, pady=2, padx=5)

        ttk.Button(gen_frame, text="生成密钥", command=self.gen_key).grid(row=0, column=3, padx=5)
        gen_frame.columnconfigure(1, weight=1)

        # 删除密钥
        del_frame = ttk.LabelFrame(self.tab_keys, text=" 删除密钥 ", padding=10)
        del_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(del_frame, text="要删除的密钥名称:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.del_key_name_var = tk.StringVar()
        ttk.Entry(del_frame, textvariable=self.del_key_name_var).grid(row=0, column=1, sticky=tk.EW, pady=2, padx=5)
        ttk.Button(del_frame, text="删除密钥", command=self.del_key).grid(row=0, column=2, padx=5)
        del_frame.columnconfigure(1, weight=1)

        # 输出信息
        log_frame = ttk.LabelFrame(self.tab_keys, text=" 密钥管理输出 ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.keys_log = scrolledtext.ScrolledText(log_frame, font=('Consolas', 9), bg="#1e1e1e", fg="#d4d4d4")
        self.keys_log.pack(fill=tk.BOTH, expand=True)

    def list_keys(self):
        exe = self.exe_path_var.get()
        self.run_cmd_async([exe, "genkey", "--list"], self.keys_log)

    def print_pubkey(self):
        exe = self.exe_path_var.get()
        self.run_cmd_async([exe, "printpub"], self.keys_log)

    def gen_key(self):
        exe = self.exe_path_var.get()
        name = self.key_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入密钥名称！")
            return
        cmd = [exe, "genkey", f"--key={name}"]
        if self.key_is_client_var.get():
            cmd.append("--client")
        self.run_cmd_async(cmd, self.keys_log)

    def del_key(self):
        exe = self.exe_path_var.get()
        name = self.del_key_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入要删除的密钥名称！")
            return
        if messagebox.askyesno("确认", f"确定要删除密钥 [{name}] 吗？"):
            self.run_cmd_async([exe, "genkey", "--delete", f"--key={name}"], self.keys_log)

    # =========================================================================
    # 4. 诊断与网络工具 Tab
    # =========================================================================
    def _build_tools_tab(self):
        tool_frame = ttk.LabelFrame(self.tab_tools, text=" 工具操作 ", padding=10)
        tool_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(tool_frame, text="目标 Tailcat 地址:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.tool_target_var = tk.StringVar()
        ttk.Entry(tool_frame, textvariable=self.tool_target_var).grid(row=0, column=1, columnspan=3, sticky=tk.EW, pady=2, padx=5)

        self.ping_until_direct_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tool_frame, text="Ping 直连测试 (--until-direct)", variable=self.ping_until_direct_var).grid(row=1, column=1, sticky=tk.W)

        # 按钮组
        btn_ping = ttk.Button(tool_frame, text="Ping 测试", command=self.run_ping)
        btn_ping.grid(row=2, column=0, padx=5, pady=5)

        btn_parse = ttk.Button(tool_frame, text="解析地址 (parse)", command=self.run_parse)
        btn_parse.grid(row=2, column=1, padx=5, pady=5)

        btn_resolve = ttk.Button(tool_frame, text="展开完整地址 (resolve)", command=self.run_resolve)
        btn_resolve.grid(row=2, column=2, padx=5, pady=5)

        btn_browse_web = ttk.Button(tool_frame, text="浏览器打开 (browse)", command=self.run_browse)
        btn_browse_web.grid(row=2, column=3, padx=5, pady=5)

        tool_frame.columnconfigure(1, weight=1)

        # 输出日志
        log_frame = ttk.LabelFrame(self.tab_tools, text=" 工具分析输出 ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tools_log = scrolledtext.ScrolledText(log_frame, font=('Consolas', 9), bg="#1e1e1e", fg="#d4d4d4")
        self.tools_log.pack(fill=tk.BOTH, expand=True)

    def run_ping(self):
        exe = self.exe_path_var.get()
        target = self.tool_target_var.get().strip()
        if not target:
            messagebox.showwarning("提示", "请输入目标 Tailcat 地址！")
            return
        cmd = [exe, "ping"]
        if self.ping_until_direct_var.get():
            cmd.append("--until-direct")
        cmd.append(target)
        self.run_cmd_async(cmd, self.tools_log)

    def run_parse(self):
        exe = self.exe_path_var.get()
        target = self.tool_target_var.get().strip()
        if not target:
            messagebox.showwarning("提示", "请输入目标 Tailcat 地址！")
            return
        self.run_cmd_async([exe, "parse", target], self.tools_log)

    def run_resolve(self):
        exe = self.exe_path_var.get()
        target = self.tool_target_var.get().strip()
        if not target:
            messagebox.showwarning("提示", "请输入目标 Tailcat 地址！")
            return
        self.run_cmd_async([exe, "resolve", target], self.tools_log)

    def run_browse(self):
        exe = self.exe_path_var.get()
        target = self.tool_target_var.get().strip()
        if not target:
            messagebox.showwarning("提示", "请输入目标 Tailcat 地址！")
            return
        self.run_cmd_async([exe, "browse", target], self.tools_log)

    def on_closing(self):
        if self.server_process:
            if messagebox.askyesno("退出确认", "服务端进程正在运行，确定要关闭程序并终止服务端吗？"):
                self.stop_server()
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = TailcatGUI()
    app.mainloop()