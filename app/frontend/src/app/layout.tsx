import "./global.css";
import Sidebar from "../components/Sidebar";

export const metadata = {
  title: "News RAG - Stock DSS",
  description: "Hệ thống hỗ trợ quyết định tin tức chứng khoán",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased font-sans">
        {/* SỬA ĐOẠN NÀY: Đổi min-h-screen thành h-screen và thêm overflow-hidden */}
        <div className="flex h-screen overflow-hidden bg-slate-50">
          <Sidebar role="ADMIN" />
          
          {/* SỬA ĐOẠN NÀY: Thêm overflow-y-auto để phần nội dung tự cuộn độc lập */}
          <main className="flex-1 overflow-y-auto overflow-x-hidden">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}