import {useEffect,useState} from "react"; import {api} from "../lib/api";
// Trang danh sách dùng chung: có trạng thái đang tải / trống / lỗi, không dùng số liệu giả
export default function TrangDanhSach({tieuDe, url, cot}:{tieuDe:string,url:string,cot:string[]}){
  const [data,setData]=useState<any[]>([]); const [loading,setLoading]=useState(true); const [error,setError]=useState("");
  useEffect(()=>{ api(url).then(setData).catch(e=>setError(e.message)).finally(()=>setLoading(false)); },[url]);
  if(loading) return <div className="p-4 sm:p-6">Đang tải dữ liệu...</div>;
  if(error) return <div className="p-6 text-red-600">Lỗi tải dữ liệu: {error}</div>;
  return <div className="p-4 sm:p-6"><h1 className="text-2xl font-bold mb-4">{tieuDe}</h1>{data.length===0?<p className="text-gray-500">Chưa có dữ liệu. Hãy thêm mới để bắt đầu.</p>:<div className="overflow-auto bg-white dark:bg-neutral-900 rounded shadow"><table className="min-w-full text-sm"><thead><tr>{cot.map(c=><th key={c} className="text-left p-3 border-b">{c}</th>)}</tr></thead><tbody>{data.map((row:any,i:number)=><tr key={i}>{cot.map(c=><td key={c} className="p-3 border-b">{String(row[c] ?? "")}</td>)}</tr>)}</tbody></table></div>}</div>;
}
