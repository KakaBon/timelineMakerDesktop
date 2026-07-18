"""程序入口。"""

from timeline_tool.application import TimelineApp


def main():
    app = TimelineApp()
    app.mainloop()


if __name__ == "__main__":
    main()