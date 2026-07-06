import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Plus, Pencil, Trash2, Star, ArrowUp, ArrowDown, Upload,
  LogOut, BarChart3, Store, LayoutGrid, Image as ImageIcon, TrendingUp,
  ClipboardCheck, CheckCircle, XCircle, ExternalLink, Globe, Phone, Navigation, Ticket, Lock, Mail,
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
  tags: [],
  imported_status: "approved",
  order: 0,
};

const emptyFeaturedLiveMusic = {
  id: "",
  city_slug: "nashville",
  active: false,
  slot: "live_music",
  title: "",
  venue_name: "",
  description: "",
  local_date: "",
  local_time: "",
  active_from: "",
  active_until: "",
  image_url: "",
  ticket_url: "",
  cta_label: "Buy Tickets",
  priority: 0,
  internal_notes: "",
};

const emptyTonightMoveSponsorship = {
  id: "",
  city_slug: "nashville",
  active: false,
  placement: "tonight_move",
  sponsor_name: "",
  sponsor_logo_url: "",
  sponsor_url: "",
  tagline: "",
  active_from: "",
  active_until: "",
  priority: 0,
  internal_notes: "",
};

const ITINERARY_BUCKET_META = {
  dinner: { label: "Dinner", className: "bg-orange-500/10 text-orange-300" },
  drinks: { label: "Drinks", className: "bg-sky-500/10 text-sky-300" },
  live_music: { label: "Live Music", className: "bg-[#C6FF00]/10 text-[#D7FF6B]" },
  late_night: { label: "Late Night", className: "bg-fuchsia-500/10 text-fuchsia-300" },
};

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(location.state?.user || null);
  const [authChecking, setAuthChecking] = useState(!location.state?.user);
  const [tab, setTab] = useState("businesses");

  const [businesses, setBusinesses] = useState([]);
  const [categories, setCategories] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsFilters, setAnalyticsFilters] = useState({
    days: "30",
    vibe: "all",
    slot: "all",
  });
  const [importSummary, setImportSummary] = useState(null);
  const [featuredLiveMusic, setFeaturedLiveMusic] = useState(emptyFeaturedLiveMusic);
  const [tonightMoveSponsorship, setTonightMoveSponsorship] = useState(emptyTonightMoveSponsorship);
  const [selectedImports, setSelectedImports] = useState([]);
  const [editing, setEditing] = useState(null); // business object or null
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [ownerInviteEmail, setOwnerInviteEmail] = useState("");
  const [ownerAccess, setOwnerAccess] = useState(null);
  const [ownerAccessLoading, setOwnerAccessLoading] = useState(false);
  const [ownerInviteSending, setOwnerInviteSending] = useState(false);
  const [ownerRevoking, setOwnerRevoking] = useState(false);
  const [savingFeaturedLiveMusic, setSavingFeaturedLiveMusic] = useState(false);
  const [savingTonightMoveSponsorship, setSavingTonightMoveSponsorship] = useState(false);
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
      const [biz, cats, tagsRes, importSummary, featured, sponsorship] = await Promise.all([
        api.get("/admin/businesses").then((r) => r.data),
        api.get("/admin/categories").then((r) => r.data),
        api.get("/admin/tags").then((r) => r.data),
        api.get("/admin/businesses/import-summary").then((r) => r.data),
        api.get("/admin/featured-events/live-music").then((r) => r.data),
        api.get("/admin/sponsorships/tonight-move").then((r) => r.data),
      ]);
      setBusinesses(biz);
      setCategories(cats);
      setAllTags(tagsRes.tags || []);
      setImportSummary(importSummary);
      setFeaturedLiveMusic({ ...emptyFeaturedLiveMusic, ...(featured || {}) });
      setTonightMoveSponsorship({ ...emptyTonightMoveSponsorship, ...(sponsorship || {}) });
    } catch (e) {
      toast.error("Failed to load admin data");
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    if (!user) return;
    setAnalyticsLoading(true);
    try {
      const params = { days: analyticsFilters.days };
      if (analyticsFilters.vibe !== "all") params.vibe = analyticsFilters.vibe;
      if (analyticsFilters.slot !== "all") params.slot = analyticsFilters.slot;
      const response = await api.get("/admin/analytics/summary", { params });
      setAnalytics(response.data);
    } catch (e) {
      toast.error("Failed to load analytics");
    } finally {
      setAnalyticsLoading(false);
    }
  }, [analyticsFilters.days, analyticsFilters.slot, analyticsFilters.vibe, user]);

  useEffect(() => {
    if (user) loadAll();
  }, [user, loadAll]);

  useEffect(() => {
    if (user) loadAnalytics();
  }, [user, loadAnalytics]);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...empty, category_slug: categories[0]?.slug || "drinks", order: businesses.length });
    setOwnerInviteEmail("");
    setOwnerAccess(null);
    setOpen(true);
  };

  const openEdit = (b) => {
    setEditing(b);
    setForm({ ...empty, ...b });
    setOwnerInviteEmail("");
    setOwnerAccessLoading(true);
    api
      .get(`/admin/businesses/${b.id}/owner-access`)
      .then((r) => {
        setOwnerAccess(r.data);
        setOwnerInviteEmail(r.data?.invite?.email || r.data?.owner?.email || "");
      })
      .catch(() => {
        toast.error("Failed to load owner access");
      })
      .finally(() => setOwnerAccessLoading(false));
    setOpen(true);
  };

  const handleSaveFeaturedLiveMusic = async () => {
    if (!featuredLiveMusic.title || !featuredLiveMusic.venue_name) {
      toast.error("Title and venue name are required");
      return;
    }
    setSavingFeaturedLiveMusic(true);
    try {
      const response = await api.put("/admin/featured-events/live-music", featuredLiveMusic);
      setFeaturedLiveMusic({ ...emptyFeaturedLiveMusic, ...response.data });
      toast.success("Featured live music event saved");
    } catch (e) {
      toast.error("Failed to save featured live music event");
    } finally {
      setSavingFeaturedLiveMusic(false);
    }
  };

  const handleDeleteFeaturedLiveMusic = async () => {
    if (!featuredLiveMusic.id) {
      setFeaturedLiveMusic(emptyFeaturedLiveMusic);
      return;
    }
    try {
      await api.delete(`/admin/featured-events/live-music/${featuredLiveMusic.id}`);
      setFeaturedLiveMusic(emptyFeaturedLiveMusic);
      toast.success("Featured live music event cleared");
    } catch (e) {
      toast.error("Failed to clear featured live music event");
    }
  };

  const handleSaveTonightMoveSponsorship = async () => {
    if (!tonightMoveSponsorship.sponsor_name) {
      toast.error("Sponsor name is required");
      return;
    }
    setSavingTonightMoveSponsorship(true);
    try {
      const response = await api.put("/admin/sponsorships/tonight-move", tonightMoveSponsorship);
      setTonightMoveSponsorship({ ...emptyTonightMoveSponsorship, ...response.data });
      toast.success("Tonight's Move sponsorship saved");
    } catch (e) {
      toast.error("Failed to save Tonight's Move sponsorship");
    } finally {
      setSavingTonightMoveSponsorship(false);
    }
  };

  const handleDeleteTonightMoveSponsorship = async () => {
    if (!tonightMoveSponsorship.id) {
      setTonightMoveSponsorship(emptyTonightMoveSponsorship);
      return;
    }
    try {
      await api.delete(`/admin/sponsorships/tonight-move/${tonightMoveSponsorship.id}`);
      setTonightMoveSponsorship(emptyTonightMoveSponsorship);
      toast.success("Tonight's Move sponsorship cleared");
    } catch (e) {
      toast.error("Failed to clear Tonight's Move sponsorship");
    }
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
      // Logout is best-effort; still navigate home even if the server call fails.
      if (process.env.NODE_ENV === "development") {
        console.warn("[auth] logout failed:", e?.message);
      }
    }
    navigate("/");
  };

  const handleBulkImportReview = async (imported_status) => {
    if (selectedImports.length === 0) return;
    try {
      await api.post("/admin/businesses/import-review", {
        ids: selectedImports,
        imported_status,
      });
      toast.success(`${selectedImports.length} place${selectedImports.length === 1 ? "" : "s"} ${imported_status}`);
      setSelectedImports([]);
      await loadAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Bulk review failed");
    }
  };

  const handleSendOwnerInvite = async () => {
    if (!editing?.id) return;
    setOwnerInviteSending(true);
    try {
      const response = await api.post(`/admin/businesses/${editing.id}/owner-invite`, {
        email: ownerInviteEmail,
      });
      setOwnerAccess(response.data);
      setOwnerInviteEmail(response.data?.invite?.email || response.data?.owner?.email || "");
      toast.success(
        response.data?.invite?.delivery_status === "provider_unconfigured"
          ? "Invite saved, but email sending is not configured."
          : "Owner invite sent"
      );
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to send owner invite");
    } finally {
      setOwnerInviteSending(false);
    }
  };

  const handleRevokeOwnerAccess = async () => {
    if (!editing?.id) return;
    setOwnerRevoking(true);
    try {
      const response = await api.post(`/admin/businesses/${editing.id}/owner-access/revoke`);
      setOwnerAccess(response.data);
      setOwnerInviteEmail("");
      toast.success("Owner access revoked");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to revoke owner access");
    } finally {
      setOwnerRevoking(false);
    }
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
          <div className="w-9 h-9 rounded-full bg-[#7C3AED] flex items-center justify-center text-white font-black">
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
            { id: "sponsorships", label: "Sponsorships", icon: Star },
            { id: "imports", label: `Import Review${importSummary?.pending ? ` (${importSummary.pending})` : ""}`, icon: ClipboardCheck },
            { id: "analytics", label: "Analytics", icon: BarChart3 },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${
                tab === t.id
                  ? "border-[#7C3AED] text-white"
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
        {tab === "sponsorships" && (
          <SponsorshipsPanel
            featuredLiveMusic={featuredLiveMusic}
            onFeaturedLiveMusicChange={setFeaturedLiveMusic}
            onSaveFeaturedLiveMusic={handleSaveFeaturedLiveMusic}
            onDeleteFeaturedLiveMusic={handleDeleteFeaturedLiveMusic}
            savingFeaturedLiveMusic={savingFeaturedLiveMusic}
            tonightMoveSponsorship={tonightMoveSponsorship}
            onTonightMoveSponsorshipChange={setTonightMoveSponsorship}
            onSaveTonightMoveSponsorship={handleSaveTonightMoveSponsorship}
            onDeleteTonightMoveSponsorship={handleDeleteTonightMoveSponsorship}
            savingTonightMoveSponsorship={savingTonightMoveSponsorship}
          />
        )}
        {tab === "analytics" && (
          <AnalyticsPanel
            analytics={analytics}
            analyticsLoading={analyticsLoading}
            filters={analyticsFilters}
            onFiltersChange={setAnalyticsFilters}
            categories={categories}
            onOpenBusiness={(bid) => navigate(`/admin/business/${bid}`)}
          />
        )}
        {tab === "imports" && (
          <ImportReviewPanel
            businesses={businesses}
            summary={importSummary}
            selected={selectedImports}
            onSelectedChange={setSelectedImports}
            onApprove={() => handleBulkImportReview("approved")}
            onReject={() => handleBulkImportReview("rejected")}
            onEdit={openEdit}
          />
        )}
      </div>

      {/* Edit / create dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-[#121218] border-white/10 text-white max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="business-dialog">
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
                className="bg-[#1A1A22] border-white/10 text-white"
                data-testid="business-form-name"
              />
            </Field>
            <Field label="Description">
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                className="bg-[#1A1A22] border-white/10 text-white"
                data-testid="business-form-description"
              />
            </Field>
            <Field label="Category">
              <Select
                value={form.category_slug}
                onValueChange={(v) => setForm({ ...form, category_slug: v })}
              >
                <SelectTrigger className="bg-[#1A1A22] border-white/10 text-white" data-testid="business-form-category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#121218] border-white/10 text-white">
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
                  <div className="w-full h-40 rounded-2xl overflow-hidden bg-[#1A1A22]">
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
                    className="border-white/10 bg-[#1A1A22] hover:bg-[#222] text-white"
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
                  className="bg-[#1A1A22] border-white/10 text-white"
                  data-testid="business-form-image-url"
                />
              </div>
            </Field>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Website">
                <Input
                  value={form.website}
                  onChange={(e) => setForm({ ...form, website: e.target.value })}
                  className="bg-[#1A1A22] border-white/10 text-white"
                  data-testid="business-form-website"
                />
              </Field>
              <Field label="Phone">
                <Input
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  className="bg-[#1A1A22] border-white/10 text-white"
                  data-testid="business-form-phone"
                />
              </Field>
            </div>

            {form.import_source === "google_places" && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Import review status">
                  <Select
                    value={form.imported_status || "pending"}
                    onValueChange={(v) => setForm({ ...form, imported_status: v })}
                  >
                    <SelectTrigger className="bg-[#1A1A22] border-white/10 text-white" data-testid="business-form-import-status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#121218] border-white/10 text-white">
                      <SelectItem value="pending" className="focus:bg-white/10 focus:text-white">Pending review</SelectItem>
                      <SelectItem value="approved" className="focus:bg-white/10 focus:text-white">Approved</SelectItem>
                      <SelectItem value="rejected" className="focus:bg-white/10 focus:text-white">Rejected</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Google rating">
                  <div className="text-sm text-white py-3">
                    {form.google_rating || "—"} · {(form.google_user_rating_count || 0).toLocaleString()} reviews
                  </div>
                </Field>
              </div>
            )}
            <Field label="Address">
              <Input
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
                className="bg-[#1A1A22] border-white/10 text-white"
                data-testid="business-form-address"
              />
            </Field>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Sponsor tier">
                <Select
                  value={form.sponsor_tier || "none"}
                  onValueChange={(v) => setForm({ ...form, sponsor_tier: v, featured: v !== "none" })}
                >
                  <SelectTrigger className="bg-[#1A1A22] border-white/10 text-white" data-testid="business-form-sponsor-tier">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#121218] border-white/10 text-white">
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
                            ? "bg-[#7C3AED]/10 border-[#7C3AED]/40 text-white"
                            : "bg-[#1A1A22] border-white/10 text-[#A1A1AA] hover:text-white"
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
                          className="w-4 h-4 accent-[#7C3AED]"
                          data-testid={`business-form-slot-${s.slug}`}
                        />
                        <span>{s.label}</span>
                      </label>
                    );
                  })}
                </div>
              </Field>
            </div>

            <Field label="Recommendation tags">
              <div className="flex flex-wrap gap-1.5" data-testid="business-form-tags">
                {allTags.map((t) => {
                  const checked = (form.tags || []).includes(t);
                  return (
                    <button
                      type="button"
                      key={t}
                      onClick={() => {
                        const cur = new Set(form.tags || []);
                        if (checked) cur.delete(t);
                        else cur.add(t);
                        setForm({ ...form, tags: Array.from(cur) });
                      }}
                      className={`px-2.5 py-1 rounded-full text-[11px] uppercase tracking-wider font-bold border transition-colors ${
                        checked
                          ? "bg-[#C6FF00]/15 border-[#C6FF00]/50 text-[#C6FF00]"
                          : "bg-[#1A1A22] border-white/10 text-[#A1A1AA] hover:text-white hover:border-white/30"
                      }`}
                      data-testid={`business-form-tag-${t}`}
                    >
                      {t}
                    </button>
                  );
                })}
              </div>
              <p className="text-[10px] text-white/40 mt-2">
                Tags drive the mood-aware recommendation engine. Pick everything that genuinely
                applies — be honest, not aspirational.
              </p>
            </Field>

            {editing ? (
              <div className="border border-white/10 bg-[#0D0D12] p-5 space-y-4" data-testid="business-owner-access-panel">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wide text-[#A1A1AA]">Business Owner Access</div>
                    <p className="mt-2 text-sm text-white/60">
                      Send a create-account invitation and manage business portal access.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.18em]">
                    <span className="px-3 py-1 rounded-full bg-white/5 text-white/60" data-testid="business-owner-portal-status">
                      {ownerAccess?.portal_access_active ? "Portal active" : "Portal inactive"}
                    </span>
                    <span className="px-3 py-1 rounded-full bg-white/5 text-white/60" data-testid="business-owner-invite-status">
                      Invite {ownerAccess?.invite?.status || "none"}
                    </span>
                  </div>
                </div>

                {ownerAccessLoading ? (
                  <div className="text-sm text-[#A1A1AA]">Loading owner access…</div>
                ) : (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.2em] text-white/35">Owner email</div>
                        <div className="mt-1 text-white/80" data-testid="business-owner-email-display">
                          {ownerAccess?.owner?.email || ownerAccess?.invite?.email || "—"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.2em] text-white/35">Last invite sent</div>
                        <div className="mt-1 text-white/80">
                          {ownerAccess?.invite?.sent_at || "—"}
                        </div>
                      </div>
                    </div>

                    <Field label="Invite owner">
                      <div className="flex flex-col sm:flex-row gap-3">
                        <Input
                          value={ownerInviteEmail}
                          onChange={(e) => setOwnerInviteEmail(e.target.value)}
                          placeholder="owner@example.com"
                          className="bg-[#1A1A22] border-white/10 text-white"
                          data-testid="business-owner-invite-email"
                        />
                        <Button
                          type="button"
                          onClick={handleSendOwnerInvite}
                          disabled={ownerInviteSending}
                          className="bg-[#7C3AED] hover:bg-[#6D28D9] text-white"
                          data-testid="business-owner-invite-send"
                        >
                          <Mail className="w-4 h-4 mr-2" />
                          {ownerInviteSending ? "Sending…" : "Invite Owner"}
                        </Button>
                      </div>
                    </Field>

                    <div className="text-xs text-white/45 leading-relaxed">
                      {ownerAccess?.invite?.delivery_status === "provider_unconfigured"
                        ? "Invite is saved, but email sending is not configured yet."
                        : "Magic links expire after 7 days and can only be claimed once."}
                    </div>

                    <Button
                      type="button"
                      variant="ghost"
                      onClick={handleRevokeOwnerAccess}
                      disabled={ownerRevoking}
                      className="text-red-300 hover:text-red-200 hover:bg-red-500/10"
                      data-testid="business-owner-revoke-access"
                    >
                      {ownerRevoking ? "Revoking…" : "Revoke access"}
                    </Button>
                  </>
                )}
              </div>
            ) : null}
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
              className="bg-[#7C3AED] hover:bg-[#6D28D9] text-white"
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

function ImportReviewPanel({ businesses, summary, selected, onSelectedChange, onApprove, onReject, onEdit }) {
  const [status, setStatus] = useState("pending");
  const imported = businesses
    .filter((b) => b.import_source === "google_places" && b.imported_status === status)
    .sort((a, b) => (b.brand_fit_score || 0) - (a.brand_fit_score || 0));
  const selectedSet = new Set(selected);

  const toggle = (id) => {
    onSelectedChange(
      selectedSet.has(id)
        ? selected.filter((selectedId) => selectedId !== id)
        : [...selected, id]
    );
  };

  const toggleAll = () => {
    const ids = imported.map((b) => b.id);
    const allSelected = ids.length > 0 && ids.every((id) => selectedSet.has(id));
    onSelectedChange(allSelected ? selected.filter((id) => !ids.includes(id)) : Array.from(new Set([...selected, ...ids])));
  };

  return (
    <div data-testid="admin-import-review">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div>
          <h2 className="font-display text-3xl font-bold">Google Places Import Review</h2>
          <p className="text-sm text-[#A1A1AA] mt-1">
            Imported places stay private until approved.
          </p>
        </div>
        <div className="flex gap-2 text-xs">
          {["pending", "approved", "rejected"].map((item) => (
            <button
              key={item}
              onClick={() => {
                setStatus(item);
                onSelectedChange([]);
              }}
              className={`px-3 py-2 rounded-full border capitalize ${
                status === item ? "border-[#7C3AED] text-white bg-[#7C3AED]/15" : "border-white/10 text-[#A1A1AA]"
              }`}
              data-testid={`admin-import-filter-${item}`}
            >
              {item} {summary?.[item] || 0}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <Button
          onClick={onApprove}
          disabled={selected.length === 0}
          className="bg-emerald-600 hover:bg-emerald-500 text-white"
          data-testid="admin-import-approve"
        >
          <CheckCircle className="w-4 h-4 mr-2" />
          Approve selected
        </Button>
        <Button
          onClick={onReject}
          disabled={selected.length === 0}
          className="bg-red-700 hover:bg-red-600 text-white"
          data-testid="admin-import-reject"
        >
          <XCircle className="w-4 h-4 mr-2" />
          Reject selected
        </Button>
      </div>

      <div className="bg-[#121218] rounded-3xl border border-white/10 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-[#A1A1AA]">
              <th className="px-5 py-4">
                <input type="checkbox" onChange={toggleAll} aria-label="Select all imported places" />
              </th>
              <th className="px-3 py-4">Place</th>
              <th className="px-3 py-4">Fit</th>
              <th className="px-3 py-4">Google</th>
              <th className="px-3 py-4 hidden lg:table-cell">Tags</th>
              <th className="px-3 py-4 hidden md:table-cell">Slots</th>
              <th className="px-5 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {imported.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-[#A1A1AA]">
                  No {status} Google Places imports.
                </td>
              </tr>
            ) : imported.map((b) => (
              <tr key={b.id} className="border-t border-white/5" data-testid={`admin-import-row-${b.id}`}>
                <td className="px-5 py-4">
                  <input
                    type="checkbox"
                    checked={selectedSet.has(b.id)}
                    onChange={() => toggle(b.id)}
                    aria-label={`Select ${b.name}`}
                  />
                </td>
                <td className="px-3 py-4">
                  <div className="font-bold">{b.name}</div>
                  <div className="text-xs text-[#A1A1AA] mt-1 max-w-sm">{b.address}</div>
                </td>
                <td className="px-3 py-4 font-bold text-[#C6FF00]">{b.brand_fit_score || "—"}</td>
                <td className="px-3 py-4 whitespace-nowrap text-[#A1A1AA]">
                  <div>{b.google_rating || "—"} · {(b.google_user_rating_count || 0).toLocaleString()}</div>
                  {b.import_override_reason && (
                    <div className="text-amber-400 text-[10px] uppercase tracking-wide mt-1">
                      Curator override
                    </div>
                  )}
                  {b.google_maps_url && (
                    <a href={b.google_maps_url} target="_blank" rel="noopener noreferrer" className="text-[#C6FF00] inline-flex items-center gap-1 mt-1">
                      Maps <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </td>
                <td className="px-3 py-4 hidden lg:table-cell text-xs text-[#A1A1AA] max-w-xs">
                  {(b.tags || []).join(", ")}
                </td>
                <td className="px-3 py-4 hidden md:table-cell text-xs text-[#A1A1AA]">
                  {(b.slots || []).join(", ")}
                </td>
                <td className="px-5 py-4 text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(b)}
                    className="text-white/70 hover:text-white hover:bg-white/5"
                    data-testid={`admin-import-edit-${b.id}`}
                  >
                    <Pencil className="w-4 h-4 mr-1" />
                    Edit
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FeaturedLiveMusicPanel({ value, onChange, onSave, onDelete, saving }) {
  return (
    <div className="mb-8 rounded-3xl border border-white/10 bg-[#121218] p-6" data-testid="admin-featured-live-music">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="font-display text-3xl font-bold">Featured Live Music Event</h2>
          <p className="mt-1 text-sm text-[#A1A1AA]">
            Overrides the Tonight page LIVE MUSIC step while active. If none is active, the normal Ticketmaster cadence applies.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] ${
            value.active ? "bg-[#C6FF00]/10 text-[#D7FF6B]" : "bg-white/5 text-white/45"
          }`}>
            {value.active ? "Active" : "Inactive"}
          </span>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Field label="Title">
          <Input
            value={value.title}
            onChange={(e) => onChange({ ...value, title: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-title"
          />
        </Field>
        <Field label="Venue name">
          <Input
            value={value.venue_name}
            onChange={(e) => onChange({ ...value, venue_name: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-venue-name"
          />
        </Field>
        <Field label="Local date">
          <Input
            type="date"
            value={value.local_date}
            onChange={(e) => onChange({ ...value, local_date: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-local-date"
          />
        </Field>
        <Field label="Show time">
          <Input
            type="time"
            value={value.local_time}
            onChange={(e) => onChange({ ...value, local_time: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-local-time"
          />
        </Field>
        <Field label="Active from">
          <Input
            type="datetime-local"
            value={value.active_from}
            onChange={(e) => onChange({ ...value, active_from: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-active-from"
          />
        </Field>
        <Field label="Active until">
          <Input
            type="datetime-local"
            value={value.active_until}
            onChange={(e) => onChange({ ...value, active_until: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-active-until"
          />
        </Field>
        <Field label="Image URL">
          <Input
            value={value.image_url}
            onChange={(e) => onChange({ ...value, image_url: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-image-url"
          />
        </Field>
        <Field label="Ticket URL">
          <Input
            value={value.ticket_url}
            onChange={(e) => onChange({ ...value, ticket_url: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-ticket-url"
          />
        </Field>
        <Field label="CTA label">
          <Input
            value={value.cta_label}
            onChange={(e) => onChange({ ...value, cta_label: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-cta-label"
          />
        </Field>
        <Field label="Priority">
          <Input
            type="number"
            value={String(value.priority ?? 0)}
            onChange={(e) => onChange({ ...value, priority: Number(e.target.value || 0) })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-priority"
          />
        </Field>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Field label="Description">
          <Textarea
            value={value.description}
            onChange={(e) => onChange({ ...value, description: e.target.value })}
            rows={4}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-description"
          />
        </Field>
        <Field label="Internal notes">
          <Textarea
            value={value.internal_notes}
            onChange={(e) => onChange({ ...value, internal_notes: e.target.value })}
            rows={4}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="featured-live-music-internal-notes"
          />
        </Field>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-white" data-testid="featured-live-music-active-toggle">
          <input
            type="checkbox"
            checked={value.active}
            onChange={(e) => onChange({ ...value, active: e.target.checked })}
            className="h-4 w-4 accent-[#C6FF00]"
          />
          <span>Active override</span>
        </label>
        <Input
          value={value.city_slug}
          onChange={(e) => onChange({ ...value, city_slug: e.target.value })}
          className="w-40 bg-[#1A1A22] border-white/10 text-white"
          data-testid="featured-live-music-city-slug"
        />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button
          onClick={onSave}
          disabled={saving}
          className="bg-[#7C3AED] hover:bg-[#6D28D9] text-white"
          data-testid="featured-live-music-save"
        >
          {saving ? "Saving…" : "Save featured event"}
        </Button>
        <Button
          variant="ghost"
          onClick={() => onChange({ ...emptyFeaturedLiveMusic, city_slug: value.city_slug || "nashville" })}
          className="text-white/70 hover:text-white hover:bg-white/5"
          data-testid="featured-live-music-reset"
        >
          Reset form
        </Button>
        <Button
          variant="ghost"
          onClick={onDelete}
          className="text-red-300 hover:text-red-200 hover:bg-red-500/10"
          data-testid="featured-live-music-delete"
        >
          Clear featured event
        </Button>
      </div>
    </div>
  );
}

function TonightMoveSponsorshipPanel({ value, onChange, onSave, onDelete, saving }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-[#121218] p-6" data-testid="admin-tonight-move-sponsorship">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="font-display text-3xl font-bold">Tonight&apos;s Move Sponsorship</h2>
          <p className="mt-1 text-sm text-[#A1A1AA]">
            Shows a subtle sponsor treatment near the Tonight page hero without affecting itinerary selection.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] ${
            value.active ? "bg-[#C6FF00]/10 text-[#D7FF6B]" : "bg-white/5 text-white/45"
          }`}>
            {value.active ? "Active" : "Inactive"}
          </span>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Field label="Sponsor name">
          <Input
            value={value.sponsor_name}
            onChange={(e) => onChange({ ...value, sponsor_name: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-name"
          />
        </Field>
        <Field label="City slug">
          <Input
            value={value.city_slug}
            onChange={(e) => onChange({ ...value, city_slug: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-city-slug"
          />
        </Field>
        <Field label="Sponsor logo URL">
          <Input
            value={value.sponsor_logo_url}
            onChange={(e) => onChange({ ...value, sponsor_logo_url: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-logo-url"
          />
        </Field>
        <Field label="Sponsor URL">
          <Input
            value={value.sponsor_url}
            onChange={(e) => onChange({ ...value, sponsor_url: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-url"
          />
        </Field>
        <Field label="Active from">
          <Input
            type="datetime-local"
            value={value.active_from}
            onChange={(e) => onChange({ ...value, active_from: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-active-from"
          />
        </Field>
        <Field label="Active until">
          <Input
            type="datetime-local"
            value={value.active_until}
            onChange={(e) => onChange({ ...value, active_until: e.target.value })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-active-until"
          />
        </Field>
        <Field label="Priority">
          <Input
            type="number"
            value={String(value.priority ?? 0)}
            onChange={(e) => onChange({ ...value, priority: Number(e.target.value || 0) })}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-priority"
          />
        </Field>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Field label="Tagline">
          <Textarea
            value={value.tagline}
            onChange={(e) => onChange({ ...value, tagline: e.target.value })}
            rows={3}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-tagline"
          />
        </Field>
        <Field label="Internal notes">
          <Textarea
            value={value.internal_notes}
            onChange={(e) => onChange({ ...value, internal_notes: e.target.value })}
            rows={3}
            className="bg-[#1A1A22] border-white/10 text-white"
            data-testid="tonight-move-sponsorship-internal-notes"
          />
        </Field>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-white" data-testid="tonight-move-sponsorship-active-toggle">
          <input
            type="checkbox"
            checked={value.active}
            onChange={(e) => onChange({ ...value, active: e.target.checked })}
            className="h-4 w-4 accent-[#C6FF00]"
          />
          <span>Active sponsorship</span>
        </label>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button
          onClick={onSave}
          disabled={saving}
          className="bg-[#7C3AED] hover:bg-[#6D28D9] text-white"
          data-testid="tonight-move-sponsorship-save"
        >
          {saving ? "Saving…" : "Save sponsorship"}
        </Button>
        <Button
          variant="ghost"
          onClick={() => onChange({ ...emptyTonightMoveSponsorship, city_slug: value.city_slug || "nashville" })}
          className="text-white/70 hover:text-white hover:bg-white/5"
          data-testid="tonight-move-sponsorship-reset"
        >
          Reset form
        </Button>
        <Button
          variant="ghost"
          onClick={onDelete}
          className="text-red-300 hover:text-red-200 hover:bg-red-500/10"
          data-testid="tonight-move-sponsorship-delete"
        >
          Clear sponsorship
        </Button>
      </div>
    </div>
  );
}

function SponsorshipsPanel({
  featuredLiveMusic,
  onFeaturedLiveMusicChange,
  onSaveFeaturedLiveMusic,
  onDeleteFeaturedLiveMusic,
  savingFeaturedLiveMusic,
  tonightMoveSponsorship,
  onTonightMoveSponsorshipChange,
  onSaveTonightMoveSponsorship,
  onDeleteTonightMoveSponsorship,
  savingTonightMoveSponsorship,
}) {
  return (
    <div data-testid="admin-sponsorships-tab">
      <FeaturedLiveMusicPanel
        value={featuredLiveMusic}
        onChange={onFeaturedLiveMusicChange}
        onSave={onSaveFeaturedLiveMusic}
        onDelete={onDeleteFeaturedLiveMusic}
        saving={savingFeaturedLiveMusic}
      />
      <TonightMoveSponsorshipPanel
        value={tonightMoveSponsorship}
        onChange={onTonightMoveSponsorshipChange}
        onSave={onSaveTonightMoveSponsorship}
        onDelete={onDeleteTonightMoveSponsorship}
        saving={savingTonightMoveSponsorship}
      />
    </div>
  );
}

function BusinessesPanel({ businesses, categories, onCreate, onEdit, onDelete, onToggleFeatured, onReorder, onAnalytics }) {
  const [filter, setFilter] = useState("all");
  const [bucketFilter, setBucketFilter] = useState("all");
  const filtered = businesses.filter((business) => {
    const matchesCategory = filter === "all" || business.category_slug === filter;
    const matchesBucket = bucketFilter === "all" || (business.itinerary_buckets || []).includes(bucketFilter);
    return matchesCategory && matchesBucket;
  });

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h2 className="font-display text-3xl font-bold">Businesses</h2>
          <p className="text-sm text-[#A1A1AA] mt-1">{businesses.length} total</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-44 bg-[#121218] border-white/10 text-white" data-testid="admin-filter-category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#121218] border-white/10 text-white">
              <SelectItem value="all" className="focus:bg-white/10 focus:text-white">All categories</SelectItem>
              {categories.map((c) => (
                <SelectItem key={c.slug} value={c.slug} className="focus:bg-white/10 focus:text-white">
                  {c.emoji} {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={bucketFilter} onValueChange={setBucketFilter}>
            <SelectTrigger className="w-44 bg-[#121218] border-white/10 text-white" data-testid="admin-filter-bucket">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#121218] border-white/10 text-white">
              <SelectItem value="all" className="focus:bg-white/10 focus:text-white">All itinerary buckets</SelectItem>
              <SelectItem value="dinner" className="focus:bg-white/10 focus:text-white">Dinner</SelectItem>
              <SelectItem value="drinks" className="focus:bg-white/10 focus:text-white">Drinks</SelectItem>
              <SelectItem value="live_music" className="focus:bg-white/10 focus:text-white">Live Music</SelectItem>
              <SelectItem value="late_night" className="focus:bg-white/10 focus:text-white">Late Night</SelectItem>
            </SelectContent>
          </Select>
          <Button
            onClick={onCreate}
            className="bg-[#7C3AED] hover:bg-[#6D28D9] text-white rounded-full"
            data-testid="admin-create-business-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add business
          </Button>
        </div>
      </div>

      <div className="bg-[#121218] rounded-3xl border border-white/10 overflow-hidden">
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
                  <div className="w-12 h-12 rounded-xl overflow-hidden bg-[#1A1A22]">
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
                  <div className="mt-2 flex flex-wrap gap-1.5" data-testid={`admin-itinerary-buckets-${b.id}`}>
                    {(b.itinerary_buckets || []).length > 0 ? (
                      b.itinerary_buckets.map((bucket) => (
                        <ItineraryBucketBadge key={`${b.id}-${bucket}`} bucket={bucket} />
                      ))
                    ) : (
                      <span className="text-[10px] uppercase tracking-[0.18em] text-white/30">No itinerary bucket</span>
                    )}
                  </div>
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

function ItineraryBucketBadge({ bucket }) {
  const meta = ITINERARY_BUCKET_META[bucket] || { label: bucket, className: "bg-white/5 text-white/45" };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] ${meta.className}`}>
      {meta.label}
    </span>
  );
}

function MetricCell({ row, field }) {
  return <span className="text-[#A1A1AA]">{(row?.[field] || 0).toLocaleString()}</span>;
}

function AnalyticsStatCard({ label, value, icon: Icon, accent = "text-[#C6FF00]" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#121218] border border-white/10 rounded-3xl p-5 sm:p-6"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-xs uppercase tracking-[0.22em] text-[#A1A1AA] font-bold">{label}</div>
        <Icon className={`w-4 h-4 ${accent}`} />
      </div>
      <div className="font-display text-4xl font-black mt-4 tracking-tight">
        {(value || 0).toLocaleString()}
      </div>
    </motion.div>
  );
}

function LeaderboardTable({ title, rows, metricLabel, metricField, onOpenBusiness, emptyCopy = "No data yet." }) {
  return (
    <div className="bg-[#121218] border border-white/10 rounded-3xl overflow-hidden">
      <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between gap-3">
        <h4 className="font-display text-lg font-bold">{title}</h4>
        <span className="text-[10px] uppercase tracking-[0.22em] text-white/35">{metricLabel}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-[0.22em] text-[#A1A1AA]">
              <th className="px-5 py-3">Business</th>
              <th className="px-3 py-3">Tier</th>
              <th className="px-3 py-3">{metricLabel}</th>
              <th className="px-3 py-3">Total</th>
            </tr>
          </thead>
          <tbody>
            {rows?.length ? (
              rows.slice(0, 8).map((row) => (
                <tr
                  key={`${title}-${row.business_id}`}
                  className="border-t border-white/5 hover:bg-white/[0.03] cursor-pointer"
                  onClick={() => onOpenBusiness(row.business_id)}
                >
                  <td className="px-5 py-3 font-medium">{row.name}</td>
                  <td className="px-3 py-3"><SponsorBadge tier={row.sponsor_tier || "none"} /></td>
                  <td className="px-3 py-3 text-[#A1A1AA]">{(row?.[metricField] || 0).toLocaleString()}</td>
                  <td className="px-3 py-3 text-white">{(row?.total_engagement || 0).toLocaleString()}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="px-5 py-8 text-center text-[#A1A1AA]">
                  {emptyCopy}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SponsorPerformanceTable({ rows }) {
  return (
    <div className="bg-[#121218] border border-white/10 rounded-3xl overflow-x-auto" data-testid="admin-sponsor-performance">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-[0.22em] text-[#A1A1AA]">
            <th className="px-5 py-4">Tier</th>
            <th className="px-3 py-4">Appearances</th>
            <th className="px-3 py-4">Locked In</th>
            <th className="px-3 py-4">Saved</th>
            <th className="px-3 py-4">Website</th>
            <th className="px-3 py-4">Directions</th>
            <th className="px-3 py-4">Buy Tickets</th>
            <th className="px-3 py-4">Phone</th>
            <th className="px-3 py-4">Total</th>
            <th className="px-3 py-4">Rate</th>
          </tr>
        </thead>
        <tbody>
          {rows?.length ? (
            rows.map((row) => (
              <tr key={row.tier} className="border-t border-white/5">
                <td className="px-5 py-3"><SponsorBadge tier={row.tier} testid={`sponsor-row-tier-${row.tier}`} /></td>
                <td className="px-3 py-3 text-[#A1A1AA]">{(row.appearances || 0).toLocaleString()}</td>
                <td className="px-3 py-3 text-[#A1A1AA]">{(row.locked_in || 0).toLocaleString()}</td>
                <td className="px-3 py-3 text-[#A1A1AA]">{(row.saved_in_final_move || 0).toLocaleString()}</td>
                <td className="px-3 py-3 text-[#A1A1AA]">{(row.website_clicks || 0).toLocaleString()}</td>
                <td className="px-3 py-3 text-[#A1A1AA]">{(row.directions_clicks || 0).toLocaleString()}</td>
                <td className="px-3 py-3 text-[#A1A1AA]">{(row.ticket_clicks || 0).toLocaleString()}</td>
                <td className="px-3 py-3 text-[#A1A1AA]">{(row.phone_clicks || 0).toLocaleString()}</td>
                <td className="px-3 py-3 text-white">{(row.total_engagement || 0).toLocaleString()}</td>
                <td className="px-3 py-3 text-[#A1A1AA]">{`${((row.engagement_rate || 0) * 100).toFixed(1)}%`}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={10} className="px-5 py-8 text-center text-[#A1A1AA]">
                No sponsor activity yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function AnalyticsPanel({ analytics, analyticsLoading, filters, onFiltersChange, categories, onOpenBusiness }) {
  if (analyticsLoading && !analytics) {
    return <div className="text-[#A1A1AA]" data-testid="admin-analytics-loading">Loading analytics…</div>;
  }
  if (!analytics) {
    return <div className="text-[#A1A1AA]" data-testid="admin-analytics-loading">Loading analytics…</div>;
  }
  const ev = analytics.by_event_type || {};
  const totals = analytics.totals || {};
  const cards = [
    { label: "Appearances", value: totals.appearances || 0, icon: Store, accent: "text-[#C6FF00]" },
    { label: "Locked In", value: totals.locked_in || 0, icon: Lock, accent: "text-[#FFD166]" },
    { label: "Saved in Final Move", value: totals.saved_in_final_move || 0, icon: ClipboardCheck, accent: "text-sky-300" },
    { label: "Website Clicks", value: totals.website_clicks || 0, icon: Globe, accent: "text-fuchsia-300" },
    { label: "Directions Clicks", value: totals.directions_clicks || 0, icon: Navigation, accent: "text-cyan-300" },
    { label: "Buy Tickets", value: totals.ticket_clicks || 0, icon: Ticket, accent: "text-orange-300" },
    { label: "Phone Clicks", value: totals.phone_clicks || 0, icon: Phone, accent: "text-emerald-300" },
    { label: "Total Engagement", value: totals.total_engagement || 0, icon: TrendingUp, accent: "text-white" },
  ];
  const catName = (slug) => categories.find((c) => c.slug === slug)?.name || slug;
  const sponsorPerf = analytics.sponsor_performance || [];
  const vibeBreakdown = analytics.vibe_breakdown || [];
  const slotBoards = analytics.slot_leaderboards || {};

  return (
    <div className="space-y-10" data-testid="admin-analytics">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h2 className="font-display text-3xl font-bold">Analytics</h2>
          <p className="text-sm text-[#A1A1AA] mt-1">Live engagement, no fluff.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-[#121218] border border-white/10 rounded-full p-1">
            {["7", "30", "90", "all"].map((days) => (
              <button
                key={days}
                onClick={() => onFiltersChange((prev) => ({ ...prev, days }))}
                className={`px-4 py-1.5 text-xs font-bold rounded-full transition-colors ${
                  filters.days === days ? "bg-[#7C3AED] text-white" : "text-[#A1A1AA] hover:text-white"
                }`}
                data-testid={`admin-analytics-range-${days}`}
              >
                {days === "all" ? "All time" : `${days}d`}
              </button>
            ))}
          </div>
          <Select
            value={filters.vibe}
            onValueChange={(value) => onFiltersChange((prev) => ({ ...prev, vibe: value }))}
          >
            <SelectTrigger className="w-56 bg-[#121218] border-white/10 text-white" data-testid="admin-analytics-filter-vibe">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#121218] border-white/10 text-white">
              <SelectItem value="all" className="focus:bg-white/10 focus:text-white">All vibes</SelectItem>
              <SelectItem value="just-vibing" className="focus:bg-white/10 focus:text-white">Take It Easy</SelectItem>
              <SelectItem value="down" className="focus:bg-white/10 focus:text-white">Let&apos;s See Where This Goes</SelectItem>
              <SelectItem value="very-down" className="focus:bg-white/10 focus:text-white">Let&apos;s Make It Count</SelectItem>
              <SelectItem value="send-it" className="focus:bg-white/10 focus:text-white">No Regrets</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={filters.slot}
            onValueChange={(value) => onFiltersChange((prev) => ({ ...prev, slot: value }))}
          >
            <SelectTrigger className="w-52 bg-[#121218] border-white/10 text-white" data-testid="admin-analytics-filter-slot">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#121218] border-white/10 text-white">
              <SelectItem value="all" className="focus:bg-white/10 focus:text-white">All slots</SelectItem>
              <SelectItem value="dinner" className="focus:bg-white/10 focus:text-white">Dinner</SelectItem>
              <SelectItem value="drinks" className="focus:bg-white/10 focus:text-white">Drinks</SelectItem>
              <SelectItem value="entertainment" className="focus:bg-white/10 focus:text-white">Entertainment / Live Music</SelectItem>
              <SelectItem value="late-night" className="focus:bg-white/10 focus:text-white">Late Night</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {cards.map((c) => (
          <AnalyticsStatCard key={c.label} {...c} />
        ))}
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">Category click heat</h3>
        <div className="bg-[#121218] border border-white/10 rounded-2xl divide-y divide-white/5">
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
        <h3 className="font-display text-xl font-bold mb-4">Category Winners</h3>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <LeaderboardTable title="Dinner" rows={slotBoards.dinner || []} metricLabel="Total" metricField="total_engagement" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Drinks" rows={slotBoards.drinks || []} metricLabel="Total" metricField="total_engagement" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Entertainment / Live Music" rows={slotBoards.entertainment || []} metricLabel="Total" metricField="total_engagement" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Late Night" rows={slotBoards["late-night"] || []} metricLabel="Total" metricField="total_engagement" onOpenBusiness={onOpenBusiness} />
        </div>
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">Winners</h3>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <LeaderboardTable title="Most Locked In" rows={analytics.top_locked_in_businesses || []} metricLabel="Locked In" metricField="locked_in" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Most Saved in Final Move" rows={analytics.top_saved_in_final_move_businesses || []} metricLabel="Saved" metricField="saved_in_final_move" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Top Click-Through Businesses" rows={analytics.top_click_through_businesses || []} metricLabel="Clicks" metricField="total_click_through" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Top Businesses by Total Engagement" rows={analytics.top_businesses_by_total_engagement || []} metricLabel="Total" metricField="total_engagement" onOpenBusiness={onOpenBusiness} />
        </div>
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">Click Leaders</h3>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <LeaderboardTable title="Top Website Click Businesses" rows={analytics.top_website_click_businesses || []} metricLabel="Website" metricField="website_clicks" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Top Directions Click Businesses" rows={analytics.top_directions_click_businesses || []} metricLabel="Directions" metricField="directions_clicks" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Top Buy Tickets Click Businesses" rows={analytics.top_ticket_click_businesses || []} metricLabel="Buy Tickets" metricField="ticket_clicks" onOpenBusiness={onOpenBusiness} />
          <LeaderboardTable title="Top Phone Click Businesses" rows={analytics.top_phone_click_businesses || []} metricLabel="Phone" metricField="phone_clicks" onOpenBusiness={onOpenBusiness} />
        </div>
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">Sponsor Performance</h3>
        <SponsorPerformanceTable rows={sponsorPerf} />
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">Top sponsor performers</h3>
        <div className="bg-[#121218] border border-white/10 rounded-2xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[#A1A1AA]">
                <th className="px-5 py-4">Business</th>
                <th className="px-3 py-4">Tier</th>
                <th className="px-3 py-4">Appearances</th>
                <th className="px-3 py-4">Locked In</th>
                <th className="px-3 py-4">Saved</th>
                <th className="px-3 py-4">Website</th>
                <th className="px-3 py-4">Directions</th>
                <th className="px-3 py-4">Buy Tickets</th>
                <th className="px-3 py-4">Phone</th>
                <th className="px-3 py-4">Total</th>
                <th className="px-3 py-4">Rate</th>
              </tr>
            </thead>
            <tbody>
              {(analytics.top_sponsor_businesses || []).length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-5 py-8 text-center text-[#A1A1AA]">
                    No sponsor businesses yet.
                  </td>
                </tr>
              ) : (
                (analytics.top_sponsor_businesses || []).map((row) => (
                  <tr
                    key={row.business_id}
                    className="border-t border-white/5 hover:bg-white/[0.03] cursor-pointer"
                    onClick={() => onOpenBusiness(row.business_id)}
                  >
                    <td className="px-5 py-3 font-medium">{row.name}</td>
                    <td className="px-3 py-3"><SponsorBadge tier={row.sponsor_tier || "none"} /></td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.appearances || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.locked_in || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.saved_in_final_move || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.website_clicks || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.directions_clicks || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.ticket_clicks || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.phone_clicks || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-white">{(row.total_engagement || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{`${((row.engagement_rate || 0) * 100).toFixed(1)}%`}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">Stats by vibe</h3>
        <div className="bg-[#121218] border border-white/10 rounded-2xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[#A1A1AA]">
                <th className="px-5 py-4">Vibe</th>
                <th className="px-3 py-4">Appearances</th>
                <th className="px-3 py-4">Locked In</th>
                <th className="px-3 py-4">Saved</th>
                <th className="px-3 py-4">Buy Tickets</th>
                <th className="px-3 py-4">Total</th>
              </tr>
            </thead>
            <tbody>
              {vibeBreakdown.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-[#A1A1AA]">
                    No vibe analytics yet.
                  </td>
                </tr>
              ) : (
                vibeBreakdown.map((row) => (
                  <tr key={row.vibe} className="border-t border-white/5">
                    <td className="px-5 py-3 font-medium">{row.vibe}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.appearances || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.locked_in || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.saved_in_final_move || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{(row.ticket_clicks || 0).toLocaleString()}</td>
                    <td className="px-3 py-3 text-white">{(row.total_engagement || 0).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="font-display text-xl font-bold mb-4">All business performance</h3>
        <div className="bg-[#121218] border border-white/10 rounded-2xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[#A1A1AA]">
                <th className="px-5 py-4">Business</th>
                <th className="px-3 py-4">Tier</th>
                <th className="px-3 py-4">Appearances</th>
                <th className="px-3 py-4">Locked In</th>
                <th className="px-3 py-4">Saved</th>
                <th className="px-3 py-4">Website</th>
                <th className="px-3 py-4">Directions</th>
                <th className="px-3 py-4">Buy Tickets</th>
                <th className="px-3 py-4">Phone</th>
                <th className="px-3 py-4">Total</th>
              </tr>
            </thead>
            <tbody>
              {analytics.by_business.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-5 py-8 text-center text-[#A1A1AA]">
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
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.appearances || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.locked_in || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.saved_in_final_move || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.website_clicks || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.directions_clicks || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.ticket_clicks || 0}</td>
                    <td className="px-3 py-3 text-[#A1A1AA]">{row.phone_clicks || 0}</td>
                    <td className="px-3 py-3 text-white">{row.total_engagement || 0}</td>
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
