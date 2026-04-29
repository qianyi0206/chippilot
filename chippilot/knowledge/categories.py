"""7 knowledge categories with keyword mapping for document classification."""

CATEGORIES = {
    "eda": {
        "description": "EDA tools: VCS, Verdi, DC, PT, Helium, Xcelium, license management",
        "keywords": [
            "vcs", "verdi", "design compiler", "dc_shell", "primetime", "pt_shell",
            "helium", "xcelium", "eda", "synopsys", "cadence", "license",
            "simulation", "synthesis", "sta", "emulation", "tool",
            "rocky", "platform", "eda-tools",
        ],
    },
    "lsf": {
        "description": "LSF job management: bsub, bjobs, queues, SSUSP, USUSP, resource planning",
        "keywords": [
            "lsf", "bsub", "bjobs", "bqueues", "bhist", "bkill", "bmod",
            "ssusp", "ususp", "queue", "resource", "job", "host", "ncpu",
            "mxj", "share", "suspend", "simv", "计算队列", "队列",
        ],
    },
    "git": {
        "description": "Git workflows: PR, branch, tag, hotfix, subtree, multi-repo",
        "keywords": [
            "git", "branch", "tag", "commit", "pr", "pull-request", "bitbucket",
            "hotfix", "subtree", "merge", "rebase", "仓库", "push-in",
            "committer", "remote-commit", "回退",
        ],
    },
    "storage": {
        "description": "Storage: quotas, disk policies, snapshots, NetApp, cleanup",
        "keywords": [
            "storage", "quota", "disk", "snapshot", "netapp", "磁盘",
            "存储", "卷快照", "数据统计", "关键存储路径",
        ],
    },
    "monitoring": {
        "description": "Monitoring: Grafana, job_monitor, CMDB, host status, CMN",
        "keywords": [
            "monitor", "grafana", "cmdb", "cmn", "host", "dns",
            "状态", "指标", "监控", "操作手册",
        ],
    },
    "scripts": {
        "description": "Scripts & utilities: setws, rel_csr, ip_version, collect_verilog",
        "keywords": [
            "setws", "rel-csr", "collect-verilog", "ip-version", "ip版本",
            "setup-project", "run-helium", "review-reg",
            "脚本", "发布版本", "生成",
        ],
    },
    "workflow": {
        "description": "Workflows: Jira, push-in flow, review, project setup, multi-repo delivery",
        "keywords": [
            "jira", "workflow", "flow", "review", "setup", "project",
            "confluence", "soc", "多仓库", "交付", "push-in",
            "checklist", "评估", "ip评估", "工作站",
        ],
    },
}
