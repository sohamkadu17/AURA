"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, Circle, Plus, Trash2, Calendar, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";

type Task = {
  id: number;
  title: string;
  description?: string;
  due_date?: string;
  priority: "low" | "medium" | "high";
  is_completed: boolean;
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newTaskTitle, setNewTaskTitle] = useState("");

  const fetchTasks = async () => {
    try {
      const res = await api.get("/tasks/?include_completed=false");
      setTasks(res.data);
    } catch (err) {
      toast.error("Failed to load tasks");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    try {
      const res = await api.post("/tasks/", { title: newTaskTitle, priority: "medium" });
      setTasks([...tasks, res.data]);
      setNewTaskTitle("");
      toast.success("Task added");
    } catch (err) {
      toast.error("Failed to create task");
    }
  };

  const toggleTask = async (task: Task) => {
    try {
      // Optimistic update
      setTasks(tasks.filter((t) => t.id !== task.id));
      await api.patch(`/tasks/${task.id}`, { is_completed: !task.is_completed });
      toast("Task completed!", { icon: "🎉" });
    } catch (err) {
      toast.error("Failed to update task");
      fetchTasks(); // Revert on failure
    }
  };

  const deleteTask = async (id: number) => {
    try {
      setTasks(tasks.filter((t) => t.id !== id));
      await api.delete(`/tasks/${id}`);
      toast.success("Task deleted");
    } catch (err) {
      toast.error("Failed to delete task");
      fetchTasks();
    }
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 h-full overflow-y-auto max-w-4xl mx-auto w-full">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Tasks & Planner</h1>
        <p className="text-gray-400 mt-2">Manage your assignments, deadlines, and reminders.</p>
      </div>

      <div className="glass-panel p-6 rounded-2xl mb-8">
        <form onSubmit={handleCreateTask} className="flex space-x-4">
          <input
            type="text"
            value={newTaskTitle}
            onChange={(e) => setNewTaskTitle(e.target.value)}
            placeholder="Add a new task..."
            className="flex-1 bg-surface border border-border rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <button
            type="submit"
            disabled={!newTaskTitle.trim()}
            className="bg-primary hover:bg-primary-hover text-white rounded-xl px-6 font-medium flex items-center transition-colors disabled:opacity-50"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add
          </button>
        </form>
      </div>

      <div className="space-y-3">
        {tasks.length === 0 ? (
          <div className="text-center py-12 border border-white/5 border-dashed rounded-2xl">
            <CheckCircle2 className="w-12 h-12 text-primary/40 mx-auto mb-3" />
            <p className="text-gray-400">All caught up! You have no pending tasks.</p>
          </div>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              className="group glass p-4 rounded-2xl flex items-center justify-between hover:bg-surface/60 transition-colors"
            >
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => toggleTask(task)}
                  className="text-gray-500 hover:text-primary transition-colors focus:outline-none"
                >
                  <Circle className="w-6 h-6" />
                </button>
                <div>
                  <h3 className="text-white font-medium">{task.title}</h3>
                  {task.due_date && (
                    <div className="flex items-center text-xs text-gray-500 mt-1">
                      <Calendar className="w-3 h-3 mr-1" />
                      {new Date(task.due_date).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
              
              <button
                onClick={() => deleteTask(task.id)}
                className="opacity-0 group-hover:opacity-100 p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all focus:outline-none"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
