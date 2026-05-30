"""
utils/paginator.py

Komponen Select menu dengan pagination (halaman) yang bisa dipakai ulang di
seluruh cog. Discord membatasi 1 Select menu maksimal 25 opsi. Ketika sebuah
kategori/game punya lebih dari 25 produk, view ini membagi opsi menjadi
beberapa halaman (default 25/halaman) dan menambahkan tombol navigasi
◀ Sebelumnya / Berikutnya ▶ supaya SEMUA produk tetap bisa dipilih member.

Cara pakai:

    from utils.paginator import PaginatedSelectView

    options = [discord.SelectOption(label=..., description=..., value=...), ...]

    async def on_select(interaction, value):
        # `value` = value dari opsi yang dipilih member
        ...

    view = PaginatedSelectView(
        options,
        on_select=on_select,
        placeholder="Pilih produk...",
        owner_id=interaction.user.id,   # opsional, batasi interaksi ke 1 user
    )
    await interaction.response.send_message("Pilih produk:", view=view, ephemeral=True)
"""
from typing import Awaitable, Callable, List, Optional

import discord

# Batas keras dari Discord untuk jumlah opsi per Select menu.
MAX_OPTIONS_PER_PAGE = 25

# Value khusus untuk opsi placeholder ketika daftar kosong.
_NOOP_VALUE = "__paginator_noop__"

OnSelect = Callable[[discord.Interaction, str], Awaitable[None]]
SelectFactory = Callable[[List[discord.SelectOption]], discord.ui.Select]

# Batas panjang label sebuah SelectOption menurut Discord.
MAX_LABEL_LEN = 100


def with_price(name: str, price_str: str, sep: str = " — ", max_len: int = MAX_LABEL_LEN) -> str:
    """
    Gabungkan nama produk + harga menjadi satu label Select, contoh:
    ``86 Diamond — Rp 15.000``.

    Bila gabungannya melewati batas 100 karakter, bagian NAMA yang dipotong
    sehingga harga selalu tetap terlihat.
    """
    suffix = f"{sep}{price_str}"
    if len(name) + len(suffix) > max_len:
        name = name[: max(0, max_len - len(suffix))]
    return f"{name}{suffix}"


class _PageSelect(discord.ui.Select):
    """Select internal yang hanya menampilkan opsi untuk halaman aktif."""

    def __init__(self, parent: "PaginatedSelectView"):
        self.parent_view = parent
        kwargs = dict(
            placeholder=parent._placeholder_for_page(),
            min_values=1,
            max_values=1,
            options=parent._current_options(),
        )
        # discord.py menolak custom_id=None; biarkan auto-generate bila tidak diisi.
        if parent.select_custom_id is not None:
            kwargs["custom_id"] = parent.select_custom_id
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction):
        if not await self.parent_view._check_owner(interaction):
            return
        value = self.values[0]
        if value == _NOOP_VALUE:
            # Tidak ada item nyata untuk dipilih.
            await interaction.response.defer()
            return
        await self.parent_view.on_select(interaction, value)


class _PrevButton(discord.ui.Button):
    def __init__(self, parent: "PaginatedSelectView"):
        self.parent_view = parent
        super().__init__(
            label="◀ Sebelumnya",
            style=discord.ButtonStyle.secondary,
            disabled=(parent.page == 0),
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view._change_page(interaction, -1)


class _NextButton(discord.ui.Button):
    def __init__(self, parent: "PaginatedSelectView"):
        self.parent_view = parent
        super().__init__(
            label="Berikutnya ▶",
            style=discord.ButtonStyle.secondary,
            disabled=(parent.page >= parent.total_pages - 1),
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view._change_page(interaction, +1)


class _PageIndicator(discord.ui.Button):
    def __init__(self, parent: "PaginatedSelectView"):
        super().__init__(
            label=f"Halaman {parent.page + 1}/{parent.total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=1,
        )


class PaginatedSelectView(discord.ui.View):
    """
    View berisi 1 Select menu yang dipaginasi otomatis bila opsi > 25.

    Parameters
    ----------
    options:
        Daftar lengkap ``discord.SelectOption`` (boleh > 25).
    on_select:
        Coroutine ``async def (interaction, value)`` yang dipanggil saat member
        memilih sebuah opsi. ``value`` adalah ``SelectOption.value`` terpilih.
        Bisa ``None`` bila memakai ``select_factory``.
    placeholder:
        Teks placeholder pada Select menu.
    page_size:
        Jumlah opsi per halaman (maksimal 25).
    owner_id:
        Bila diisi, hanya user dengan id ini yang boleh berinteraksi.
    select_custom_id:
        custom_id opsional untuk Select menu (umumnya tidak perlu karena view
        ini bersifat ephemeral & sementara).
    select_factory:
        Opsional. Fungsi ``(options_halaman) -> discord.ui.Select`` untuk
        membangun Select tiap halaman memakai kelas Select yang sudah ada
        (beserta callback-nya sendiri). Berguna untuk memaginasi dropdown lama
        tanpa menulis ulang logika callback-nya. Bila diisi, ``on_select``
        diabaikan.
    """

    def __init__(
        self,
        options: List[discord.SelectOption],
        on_select: Optional[OnSelect] = None,
        *,
        placeholder: str = "Pilih...",
        page_size: int = MAX_OPTIONS_PER_PAGE,
        timeout: Optional[float] = 120,
        owner_id: Optional[int] = None,
        select_custom_id: Optional[str] = None,
        select_factory: Optional[SelectFactory] = None,
    ):
        super().__init__(timeout=timeout)
        self.all_options: List[discord.SelectOption] = list(options or [])
        self.on_select = on_select
        self.base_placeholder = placeholder
        self.page_size = max(1, min(page_size, MAX_OPTIONS_PER_PAGE))
        self.owner_id = owner_id
        self.select_custom_id = select_custom_id
        self.select_factory = select_factory
        self.page = 0
        self.total_pages = max(
            1,
            (len(self.all_options) + self.page_size - 1) // self.page_size,
        )
        self._render()

    # ── Helpers ────────────────────────────────────────────────────────────
    def _current_options(self) -> List[discord.SelectOption]:
        if not self.all_options:
            return [discord.SelectOption(label="Tidak ada item tersedia", value=_NOOP_VALUE)]
        start = self.page * self.page_size
        return self.all_options[start:start + self.page_size]

    def _placeholder_for_page(self) -> str:
        if self.total_pages > 1:
            return f"{self.base_placeholder} ({self.page + 1}/{self.total_pages})"
        return self.base_placeholder

    def _render(self):
        """Bangun ulang komponen view sesuai halaman aktif."""
        self.clear_items()
        if self.select_factory is not None and self.all_options:
            self.add_item(self.select_factory(self._current_options()))
        else:
            self.add_item(_PageSelect(self))
        if self.total_pages > 1:
            self.add_item(_PrevButton(self))
            self.add_item(_PageIndicator(self))
            self.add_item(_NextButton(self))

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if self.owner_id is not None and interaction.user.id != self.owner_id:
            await interaction.response.send_message("Menu ini bukan milik kamu!", ephemeral=True)
            return False
        return True

    async def _change_page(self, interaction: discord.Interaction, delta: int):
        if not await self._check_owner(interaction):
            return
        self.page = max(0, min(self.page + delta, self.total_pages - 1))
        self._render()
        await interaction.response.edit_message(view=self)
