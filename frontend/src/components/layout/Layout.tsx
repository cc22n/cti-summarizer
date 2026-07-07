import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import { SidebarProvider, useSidebar } from "../../contexts/SidebarContext";

function LayoutInner() {
  const { open, close } = useSidebar();

  return (
    <div className="flex min-h-screen w-full bg-[#0a0e17]">
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={close}
        />
      )}
      <Sidebar />
      <main className="flex-1 overflow-auto p-6 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}

export default function Layout() {
  return (
    <SidebarProvider>
      <LayoutInner />
    </SidebarProvider>
  );
}
