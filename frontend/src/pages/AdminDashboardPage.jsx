import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Plus, Pencil, Trash2, Star, ArrowUp, ArrowDown, Upload,
  LogOut, BarChart3, Store, LayoutGrid, Image as ImageIcon, TrendingUp,
} from "lucide-react";
import { api, resolveImageUrl } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

const empty = {
  name: "",
  description: "",
  image_url: "",
  image_path: null,
  website: "",
  phone: "",
  address: "",
  category_slug: "drinks",
  city_slug: "nashville",
  featured: false,
  sponsor_tier: "none",
  slots: [],
  order: 0,
};

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(location.state?.user || null);
  const [authChecking, setAuthChecking] = useState(!location.state?.user);
  const [tab, setTab] = useState("businesses");

  const [businesses, setBusinesses] = useState([]);
  const [categories, setCategories] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [editing, setEditing] = useState(null); // business object or null
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  // Auth check
  useEffect(() => {
    if (user) return;
    api
      .get("/auth/me")
      .then((r) => {
        if (r.data.role !== "admin") {
          toast.error("You need admin access");
          navigate("/admin/login");
          return;
        }
        setUser(r.data);
        setAuthChecking(false);
      })
      .catch(() => {
        navigate("/admin/login");
      });
  }, [navigate, user]);

  const loadAll = useCallback(async () => {
    try {
      const [biz, cats, analytics] = await Promise.all([
        api.get("/admin/businesses").then((r) => r.data),
        api.get("/admin/categories").then((r) => r.data),
        api.get("/admin/analytics/summary").then((r) => r.data),
      ]);
      setBusinesses(biz);
      setCategories(cats);
      setAnalytics(analytics);
    } catch (e) {
      toast.error("Failed to load admin data");
    }
  }, []);

  useEffect(() => {
    if (user) loadAll();
  }, [user, loadAll]);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...empty, category_slug: categories[0]?.slug || "drinks", order: businesses.length });
    setOpen(true);
  };

  const openEdit = (b) => {
    setEditing(b);
    setForm({ ...empty, ...b });
    setOpen(true);
  };

  const handleSave = async () => {
    if (!form.name || !form.category_slug) {
      toast.error("Name and category are required");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await api.patch(`/admin/businesses/${editing.id}`, form);
        toast.success("Business updated");
      } else {
        await api.post("/admin/businesses", form);
        toast.success("Business created");
      }
      setOpen(false);
      await loadAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    }
    setSaving(false);
  };

  const handleDelete = async (b) => {
    if (!window.confirm(`Delete "${b.name}"?`)) return;
    try {
      await api.delete(`/admin/businesses/${b.id}`);
      toast.success("Deleted");
      await loadAll();
    } catch (e) {
      toast.error("Delete failed");
    }
  };

  const handleToggleFeatured = async (b) => {
    try {
      await api.patch(`/admin/businesses/${b.id}`, { featured: !b.featured });
      await loadAll();
    } catch (e) {
      toast.error("Failed");
    }
  };

  const handleReorder = async (idx, dir) => {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= businesses.length) return;
    const a = businesses[idx];
    const b = businesses[newIdx];
    try {
      await api.post("/admin/businesses/reorder", {
        items: [
          { id: a.id, order: b.order },
          { id: b.id, order: a.order },
        ],
      });
      await loadAll();
    } catch (e) {
      toast.error("Reorder failed");
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/admin/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setForm((f) => ({ ...f, image_path: r.data.path, image_url: "" }));
      toast.success("Image uploaded");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Upload failed");
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleLogout = async () => {
    try {
      await api.post("/auth/logout");
    } catch (e) {
      /* ignore */
    }
    navigate("/");
  };

  if (authChecking) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center text-[#A1A1AA]">
        Checking session…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white" data-testid="admin-dashboard">
      {/* Header */}
      <div className="border-b border-white/10 px-6 py-4 flex items-center justify-between sticky top-0 bg-[#050505]/95 backdrop-blur z-30">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-[#FF2A5F] flex items-center justify-center text-white font-black">
            Y
          </div>
          <div>
            <div className="font-display font-bold text-lg leading-none">You're Not Down</div>
            <div className="text-xs text-[#A1A1AA] mt-0.5">Admin · Nashville</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {user?.picture ? (
            <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
          ) : null}
          <span className="text-sm text-[#A1A1AA] hidden sm:block" data-testid="admin-user-email">
            {user?.email}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            data-testid="admin-logout-button"
            className="text-white/70 hover:text-white hover:bg-white/5"
          >
            <LogOut className="w-4 h-4 mr-1" />
            Logout
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-6 pt-6">
        <div className="flex gap-2 border-b border-white/10">
          {[
            { id: "businesses", label: "Businesses", icon: Store },
            { id: "analytics", label: "Analytics", icon: BarChart3 },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${
                tab === t.id
                  ? "border-[#FF2A5F] text-white"
                  : "border-transparent text-[#A1A1AA] hover:text-white"
              }`}
              data-testid={`admin-tab-${t.id}`}
            >
              <t.icon className="w-4 h-4" />
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-8 max-w-7xl mx-auto">
        {tab === "businesses" && (
          <BusinessesPanel
            businesses={businesses}
            categories={categories}
            onCreate={openCreate}
            onEdit={openEdit}
            onDelete={handleDelete}
            onToggleFeatured={handleToggleFeatured}
            onReorder={handleReorder}
            onAnalytics={(b) => navigate(`/admin/business/${b.id}`)}
          />
        )}
        {tab === "analytics" && <AnalyticsPanel analytics={analytics} categories={categories} onOpenBusiness={(bid) => navigate(`/admin/business/${bid}`)} />}
      </div>

      {/* Edit / create dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-[#121212] border-white/10 text-white max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="business-dialog">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl">
              {editing ? "Edit business" : "New business"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <Field label="Name">
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="bg-[#1A1A1A] border-white/10 text-white"
                data-testid="business-form-name"
              />
            </Field>
            <Field label="Description">
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                className="bg-[#1A1A1A] border-white/10 text-white"
                data-testid="business-form-description"
              />
            </Field>
            <Field label="Category">
              <Select
                value={form.category_slug}
                onValueChange={(v) => setForm({ ...form, category_slug: v })}
              >
                <SelectTrigger className="bg-[#1A1A1A] border-white/10 text-white" data-testid="business-form-category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#121212] border-white/10 text-white">
                  {categories.map((c) => (
                    <SelectItem key={c.slug} value={c.slug} className="focus:bg-white/10 focus:text-white">
                      {c.emoji} {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Image">
              <div className="space-y-3">
                {(form.image_path || form.image_url) && (
                  <div className="w-full h-40 rounded-2xl overflow-hidden bg-[#1A1A1A]">
                    <img
                      src={resolveImageUrl(form)}
                      alt="preview"
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    className="border-white/10 bg-[#1A1A1A] hover:bg-[#222] text-white"
                    data-testid="business-form-upload-button"
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    {uploading ? "Uploading…" : "Upload image"}
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleUpload}
                    data-testid="business-form-upload-input"
                  />
                </div>
                <Input
                  placeholder="...or paste an image URL"
                  value={form.image_url}
                  onChange={(e) => setForm({ ...form, image_url: e.target.value, image_path: null })}
                  className="bg-[#1A1A1A] border-white/10 text-white"
                  data-testid="business-form-image-url"
                />
              </div>
            </Field>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Website">
                <Input
                  value={form.website}
                  onChange={(e) => setForm({ ...form, website: e.target.value })}
                  className="bg-[#1A1A1A] border-white/10 text-white"
                  data-testid="business-form-website"
                />
              </Field>
              <Field label="Phone">
                <Input
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  className="bg-[#1A1A1A] border-white/10 text-white"
                  data-testid="business-form-phone"
                />
              </Field>
            </div>
            <Field label="Address">
              <Input
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
                className="bg-[#1A1A1A] border-white/10 text-white"
                data-testid="business-form-address"
              />
            </Field>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Sponsor tier">
                <Select
                  value={form.sponsor_tier || "none"}
                  onValueChange={(v) => setForm({ ...form, sponsor_tier: v, featured: v !== "none" })}
                >
                  <SelectTrigger className="bg-[#1A1A1A] border-white/10 text-white" data-testid="business-form-sponsor-tier">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#121212] border-white/10 text-white">
                    <SelectItem value="none" className="focus:bg-white/10 focus:text-white">None · weight 1</SelectItem>
                    <SelectItem value="silver" className="focus:bg-white/10 focus:text-white">Silver · weight 5</SelectItem>
                    <SelectItem value="gold" className="focus:bg-white/10 focus:text-white">Gold · weight 10</SelectItem>
                    <SelectItem value="platinum" className="focus:bg-white/10 focus:text-white">Platinum · weight 20</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Itinerary slots">
                <div className="grid grid-cols-2 gap-2" data-testid="business-form-slots">
                  {[
                    { slug: "dinner", label: "🍽️ Dinner" },
                    { slug: "drinks", label: "🍸 Drinks" },
                    { slug: "entertainment", label: "🎵 Entertainment" },
                    { slug: "late-night", label: "🌃 Late Night" },
                  ].map((s) => {
                    const checked = (form.slots || []).includes(s.slug);
                    return (
                      <label
                        key={s.slug}
                        className={`flex items-center gap-2 px-3 py-2 rounded-xl border cursor-pointer transition-colors text-sm ${
                          checked
                            ? "bg-[#FF2A5F]/10 border-[#FF2A5F]/40 text-white"
                            : "bg-[#1A1A1A] border-white/10 text-[#A1A1AA] hover:text-white"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            const cur = new Set(form.slots || []);
                            if (e.target.checked) cur.add(s.slug);
                            else cur.delete(s.slug);
                            setForm({ ...form, slots: Array.from(cur) });
                          }}
                          className="w-4 h-4 accent-[#FF2A5F]"
                          data-testid={`business-form-slot-${s.slug}`}
                        />
                        <span>{s.label}</span>
                      </label>
                    );
                  })}
                </div>
              </Field>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setOpen(false)}
              className="text-white/70 hover:text-white hover:bg-white/5"
              data-testid="business-form-cancel"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving}
              className="bg-[#FF2A5F] hover:bg-[#E01E50] text-white"
              data-testid="business-form-save"
            >
              {saving ? "Saving…" : editing ? "Save changes" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wide text-[#A1A1AA] mb-2">{label}</div>
      {children}
    </div>
  );
}

function BusinessesPanel({ businesses, categories, onCreate, onEdit, onDelete, onToggleFeatured, onReorder, onAnalytics }) {
  const [filter, setFilter] = useState("all");
  const filtered = filter === "all" ? businesses : businesses.filter((b) => b.category_slug === filter);

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h2 className="font-display text-3xl font-bold">Businesses</h2>
          <p className="text-sm text-[#A1A1AA] mt-1">{businesses.length} total</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-44 bg-[#121212] border-white/10 text-white" data-testid="admin-filter-category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#121212] border-white/10 text-white">
              <SelectItem value="all" className="focus:bg-white/10 focus:text-white">All categories</SelectItem>
              {categories.map((c) => (
                <SelectItem key={c.slug} value={c.slug} className="focus:bg-white/10 focus:text-white">
                  {c.emoji} {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={onCreate}
            className="bg-[#FF2A5F] hover:bg-[#E01E50] text-white rounded-full"
            data-testid="admin-create-business-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add business
          </Button>
        </div>
      </div>

      <div className="bg-[#121212] rounded-3xl border border-white/10 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-[#A1A1AA]">
              <th className="px-5 py-4 w-16"></th>
              <th className="px-2 py-4">Name</th>
              <th className="px-5 py-4 hidden md:table-cell">Slots</th>
              <th className="px-5 py-4 hidden sm:table-cell">Sponsor</th>
              <th className="px-5 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-12 text-center text-[#A1A1AA]" data-testid="admin-empty-businesses">
                  No businesses yet. Click "Add business" to get started.
                </td>
              </tr>
            )}
            {filtered.map((b, idx) => (
              <tr key={b.id} className="border-t border-white/5 hover:bg-white/[0.02]" data-testid={`admin-business-row-${b.id}`}>
                <td className="px-5 py-3">
                  <div className="w-12 h-12 rounded-xl overflow-hidden bg-[#1A1A1A]">
                    {resolveImageUrl(b) ? (
                      <img src={resolveImageUrl(b)} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-white/30">
                        <ImageIcon className="w-5 h-5" />
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-2 py-3">
                  <div className="font-bold text-white">{b.name}</div>
                  <div className="text-xs text-[#A1A1AA] line-clamp-1 max-w-md">{b.description}</div>
                </td>
                <td className="px-5 py-3 hidden md:table-cell text-xs text-[#A1A1AA]">
                  {(b.slots && b.slots.length > 0) ? b.slots.join(", ") : <span className="text-white/30">—</span>}
                </td>
                <td className="px-5 py-3 hidden sm:table-cell">
                  <SponsorBadge tier={b.sponsor_tier || "none"} testid={`admin-sponsor-badge-${b.id}`} />
                </td>
                <td className="px-5 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <IconBtn onClick={() => onAnalytics(b)} testid={`admin-analytics-${b.id}`} label="View analytics">
                      <TrendingUp className="w-4 h-4" />
                    </IconBtn>
                    <IconBtn onClick={() => onReorder(idx, -1)} testid={`admin-move-up-${b.id}`} label="Move up">
                      <ArrowUp className="w-4 h-4" />
                    </IconBtn>
                    <IconBtn onClick={() => onReorder(idx, 1)} testid={`admin-move-down-${b.id}`} label="Move down">
                      <ArrowDown className="w-4 h-4" />
                    </IconBtn>
                    <IconBtn onClick={() => onEdit(b)} testid={`admin-edit-${b.id}`} label="Edit">
                      <Pencil className="w-4 h-4" />
                    </IconBtn>
                    <IconBtn onClick={() => onDelete(b)} testid={`admin-delete-${b.id}`} label="Delete" danger>
                      <Trash2 className="w-4 h-4" />
                    </IconBtn>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function IconBtn({ children, onClick, testid, label, danger }) {
  return (
    <button
      onClick={onClick}
      data-testid={testid}
      aria-label={label}
      className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
        danger
          ? "text-white/60 hover:text-red-400 hover:bg-red-500/10"
          : "text-white/60 hover:text-white hover:bg-white/5"
      }`}
    >
      {children}
    </button>
  );
}

const TIER_STYLES = {
  platinum: { bg: "bg-white/15", text: "text-white", label: "PLATINUM" },
  gold: { bg: "bg-yellow-500/15", text: "text-yellow-400", label: "GOLD" },
  silver: { bg: "bg-zinc-400/15", text: "text-zinc-300", label: "SILVER" },
  none: { bg: "bg-white/5", text: "text-white/40", label: "—" },
};

function SponsorBadge({ tier, testid }) {
  const s = TIER_STYLES[tier] || TIER_STYLES.none;
  return (
    <span
      className={`inline-flex px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider ${s.bg} ${s.text}`}
      data-testid={testid}
    >
      {s.label}
    </span>
  );
}

function AnalyticsPanel({ analytics, categories, onOpenBusiness }) {
  if (!analytics) {
    return <div className="text-[#A1A1AA]" data-testid="admin-analytics-loading">Loading analytics…</div>;
  }
  const ev = analytics.by_event_type || {};
  const cards = [
    { label: "Homepage visits", value: ev.homepage_visit || 0, icon: LayoutGrid },
    { label: "I'm Down clicks", value: ev.im_down_click || 0, icon: Star },
    { label: "Vibe selections", value: ev.vibe_click || 0, icon: BarChart3 },
    { label: "Itinerary views", value: ev.itinerary_view || 0, icon: TrendingUp },
    { label: "Another Night clicks", value: ev.another_night_click || 0, icon: BarChart3 },
    { label: "Business appearances", value: ev.business_appearance || 0, icon: Store },
    { label: "Website clicks", value: ev.website_click || 0, icon: ImageIcon },
    { label: "Phone clicks", value: ev.phone_click || 0, icon: ImageIcon },
    { label: "Directions clicks", value: ev.directions_click || 0, icon: ImageIcon },
  ];
  const catName = (slug) => categories.find((c) => c.slug === slug)?.name || slug;
  const sponsorPerf = analytics.sponsor_performance || [];

  return (
    <div className="space-y-10" data-testid="admin-analytics">
      <div>
        <h2 className="font-display text-3xl font-bold">Analytics</h2>
        <p className="text-sm text-[#A1A1AA] mt-1">Live engagement, no fluff.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <motion.div
            key={c.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[#121212] border border-white/10 rounded-2xl p-5"
          >
            <div className="text-xs uppercase tracking-wide text-[#A1A1AA] font-bold">{c.label}</div>
            <div className="font-display text-3xl font-black mt-2">{c.value.toLocaleString()}</div>
          </motion.div>
        ))}
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">By category</h3>
        <div className="bg-[#121212] border border-white/10 rounded-2xl divide-y divide-white/5">
          {analytics.by_category.length === 0 ? (
            <div className="p-5 text-sm text-[#A1A1AA]">No category clicks yet.</div>
          ) : (
            analytics.by_category.map((row) => (
              <div key={row.category_slug} className="flex items-center justify-between p-4 px-5">
                <span className="font-medium">{catName(row.category_slug)}</span>
                <span className="text-[#A1A1AA]">{row.count}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">Sponsor performance</h3>
        <div className="bg-[#121212] border border-white/10 rounded-2xl overflow-x-auto" data-testid="admin-sponsor-performance">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[#A1A1AA]">
                <th className="px-5 py-4">Tier</th>
                <th className="px-3 py-4">Appearances</th>
                <th className="px-3 py-4">Website</th>
                <th className="px-3 py-4">Phone</th>
                <th className="px-3 py-4">Directions</th>
              </tr>
            </thead>
            <tbody>
              {sponsorPerf.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-[#A1A1AA]">
                    No sponsor activity yet.
                  </td>
                </tr>
              ) : (
                sponsorPerf.map((row) => (
                  <tr key={row.tier} className="border-t border-white/5">
                    <td className="px-5 py-3">
                      <SponsorBadge tier={row.tier} testid={`sponsor-row-tier-${row.tier}`} />
                    </td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.business_appearance || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.website_click || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.phone_click || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.directions_click || 0}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">By business</h3>
        <div className="bg-[#121212] border border-white/10 rounded-2xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[#A1A1AA]">
                <th className="px-5 py-4">Business</th>
                <th className="px-3 py-4">Tier</th>
                <th className="px-3 py-4">Appearances</th>
                <th className="px-3 py-4">Website</th>
                <th className="px-3 py-4">Phone</th>
                <th className="px-3 py-4">Directions</th>
              </tr>
            </thead>
            <tbody>
              {analytics.by_business.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-[#A1A1AA]">
                    No business events yet.
                  </td>
                </tr>
              ) : (
                analytics.by_business.map((row) => (
                  <tr
                    key={row.business_id}
                    className="border-t border-white/5 hover:bg-white/[0.03] cursor-pointer"
                    onClick={() => onOpenBusiness(row.business_id)}
                    data-testid={`admin-analytics-row-${row.business_id}`}
                  >
                    <td className="px-5 py-3 font-medium">{row.name}</td>
                    <td className="px-3 py-3"><SponsorBadge tier={row.sponsor_tier || "none"} /></td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.business_appearance || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.website_click || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.phone_click || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.directions_click || 0}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
