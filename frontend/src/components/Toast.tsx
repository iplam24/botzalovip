import { ReactNode, createContext, useCallback, useContext, useRef, useState } from "react";

// Toast thông báo thao tác (Đợt nâng cấp 2 mục 8/11): thay alert()/banner thô
// ở các thao tác chính. Dùng: const toast = useToast(); toast.thanhCong("..."),
// toast.loi("..."), toast.thongTin("..."). Tự biến mất sau ~3.5 giây.

type LoaiToast = "thanh_cong" | "loi" | "thong_tin";
type MucToast = { id: number; loai: LoaiToast; text: string };

const NguCanhToast = createContext<{
  day: (loai: LoaiToast, text: string) => void;
}>({ day: () => {} });

export function useToast() {
  const ctx = useContext(NguCanhToast);
  return {
    day: ctx.day,
    thanhCong: (text: string) => ctx.day("thanh_cong", text),
    loi: (text: string) => ctx.day("loi", text),
    thongTin: (text: string) => ctx.day("thong_tin", text),
  };
}

const ICON: Record<LoaiToast, string> = {
  thanh_cong: "fa-solid fa-circle-check",
  loi: "fa-solid fa-circle-exclamation",
  thong_tin: "fa-solid fa-circle-info",
};
const MAU: Record<LoaiToast, string> = {
  thanh_cong: "border-green-500 text-green-800",
  loi: "border-red-500 text-red-700",
  thong_tin: "border-blue-500 text-blue-800",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [ds, setDs] = useState<MucToast[]>([]);
  const boDem = useRef(0);

  const day = useCallback((loai: LoaiToast, text: string) => {
    const id = ++boDem.current;
    setDs((cu) => [...cu.slice(-3), { id, loai, text }]);
    setTimeout(() => setDs((cu) => cu.filter((t) => t.id !== id)), 3600);
  }, []);

  const dong = (id: number) => setDs((cu) => cu.filter((t) => t.id !== id));

  return (
    <NguCanhToast.Provider value={{ day }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[90] flex flex-col gap-2 w-[calc(100vw-2rem)] max-w-sm pointer-events-none">
        {ds.map((t) => (
          <div
            key={t.id}
            className={`toast-muc pointer-events-auto bg-white dark:bg-neutral-900 border-l-4 ${MAU[t.loai]} shadow-the rounded-lg px-3.5 py-2.5 text-sm flex items-start gap-2.5`}
            role="status"
          >
            <i className={`${ICON[t.loai]} mt-0.5`} />
            <span className="flex-1 text-gray-700 dark:text-gray-200">{t.text}</span>
            <button onClick={() => dong(t.id)} className="text-gray-400 hover:text-gray-600 px-1" aria-label="Đóng thông báo">
              <i className="fa-solid fa-xmark" />
            </button>
          </div>
        ))}
      </div>
    </NguCanhToast.Provider>
  );
}
