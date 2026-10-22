/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Màu thương hiệu kiểu Zalo — đồng bộ tinh thần với biến --mau-chu-dao (cài đặt hệ thống)
        thuongHieu: {
          50: "#eef6ff",
          100: "#d9eaff",
          200: "#bcdcff",
          300: "#8ec4ff",
          400: "#589dff",
          500: "#2f7bff",
          600: "#0068ff",
          700: "#0053d6",
          800: "#0645ad",
          900: "#0a3c8a",
        },
      },
      fontFamily: {
        sans: ['"Be Vietnam Pro"', "Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        the: "0 1px 3px rgba(16, 24, 40, 0.06), 0 4px 14px rgba(16, 24, 40, 0.05)",
        nhe: "0 1px 2px rgba(16, 24, 40, 0.05)",
      },
    },
  },
  plugins: [],
};
