"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Trophy } from "lucide-react";

interface Trend {
  date: string;
  count: number;
}

interface Category {
  category: string;
  count: number;
}

interface LeaderboardItem {
  developer_login: string;
  prs_reviewed: number;
  total_issues: number;
}

export default function Dashboard() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardItem[]>([]);
  
  // Hardcoded to team 1 for demo purposes
  const teamId = 1; 

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
    Promise.all([
      fetch(`${apiUrl}/teams/${teamId}/stats/trends`).then((res) => res.json()),
      fetch(`${apiUrl}/teams/${teamId}/stats/categories`).then((res) => res.json()),
      fetch(`${apiUrl}/teams/${teamId}/leaderboard`).then((res) => res.json()),
    ])
      .then(([trendsData, categoriesData, leaderboardData]) => {
        setTrends(Array.isArray(trendsData) ? trendsData : []);
        setCategories(Array.isArray(categoriesData) ? categoriesData : []);
        setLeaderboard(Array.isArray(leaderboardData) ? leaderboardData : []);
      })
      .catch(console.error);
  }, [teamId]);

  return (
    <main className="min-h-screen bg-gray-50 p-8 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">DevBrief Analytics</h1>
          <p className="text-gray-500 mt-2 text-sm">Code review insights and team performance</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Trends Chart */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h2 className="text-lg font-semibold mb-6 text-gray-800">Issues Trend (Last 30 Days)</h2>
            <div className="h-80 w-full text-sm">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                  <XAxis dataKey="date" stroke="#6b7280" tickLine={false} axisLine={false} dy={10} />
                  <YAxis stroke="#6b7280" tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4, strokeWidth: 0 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Categories Chart */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h2 className="text-lg font-semibold mb-6 text-gray-800">Issues by Category</h2>
            <div className="h-80 w-full text-sm">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categories} layout="vertical" margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                  <XAxis type="number" stroke="#6b7280" tickLine={false} axisLine={false} />
                  <YAxis dataKey="category" type="category" stroke="#6b7280" tickLine={false} axisLine={false} width={100} />
                  <Tooltip 
                    cursor={{ fill: '#f8fafc' }}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={24} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Leaderboard */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center gap-2 mb-6">
            <Trophy className="w-5 h-5 text-yellow-500" />
            <h2 className="text-lg font-semibold text-gray-800">Developer Leaderboard</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="py-3 px-4 font-semibold text-gray-500 uppercase tracking-wider text-xs">Developer</th>
                  <th className="py-3 px-4 font-semibold text-gray-500 uppercase tracking-wider text-xs text-right">PRs Reviewed</th>
                  <th className="py-3 px-4 font-semibold text-gray-500 uppercase tracking-wider text-xs text-right">Total Issues</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {leaderboard.map((item, index) => (
                  <tr key={index} className="hover:bg-gray-50 transition-colors">
                    <td className="py-4 px-4 font-medium text-gray-900">{item.developer_login}</td>
                    <td className="py-4 px-4 text-gray-600 text-right">{item.prs_reviewed}</td>
                    <td className="py-4 px-4 text-gray-600 text-right">
                      <span className="bg-red-50 text-red-700 py-1 px-2.5 rounded-full font-medium">
                        {item.total_issues}
                      </span>
                    </td>
                  </tr>
                ))}
                {leaderboard.length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-12 text-center text-gray-400">
                      No team data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
