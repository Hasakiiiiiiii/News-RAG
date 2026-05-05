import { redirect } from "next/navigation";

export default function RootPage() {
  // Tự động điều hướng vào Dashboard khi vừa mở web
  redirect("/dashboard");
  
  // Hoặc bạn có thể code một trang Landing Page giới thiệu ở đây
  return null;
}