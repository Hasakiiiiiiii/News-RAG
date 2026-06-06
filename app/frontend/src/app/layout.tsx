import "./global.css";
import Sidebar from "../components/Sidebar";

export const metadata = {
  title: "News RAG - Dashboard",
  description: "Hệ thống hỗ trợ truy vấn tin tức",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // Đừng quên suppressHydrationWarning ở đây nhé
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased font-sans">
        {/* Khung cố định toàn màn hình */}
        <div className="flex h-screen overflow-hidden bg-slate-50">
          <Sidebar role="ADMIN" />
          
          {/* Phần nội dung chính tự cuộn độc lập */}
          <main className="flex-1 overflow-y-auto overflow-x-hidden">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}