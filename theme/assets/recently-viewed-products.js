/* Mockers — recently viewed.
   Upstream deduped by product HANDLE. Since a design is now five products
   (<design>-<style>), viewing two garments of one design produced two identical-looking
   cards. This collapses the list to one card per DESIGN and drops the design you are
   already looking at — the style switcher on the page already covers its siblings. */
class MRecentlyViewed extends HTMLElement {
  constructor() {
    super();

    const raw = getCookie("m-recent-viewed-products");
    if (!raw) return;

    const STYLE_SUFFIX = /-(regular-fit-t-shirt|oversized-light-soft|oversized-heavy-premium|sweatshirt|hoodie)$/;
    const designOf = (handle) => handle.replace(STYLE_SUFFIX, "");

    let handles;
    try {
      handles = Array.from(new Set(JSON.parse(raw)));
    } catch (e) {
      return;
    }

    const current = this.dataset.productHandle;
    if (current) handles = handles.filter((h) => h !== current);
    const currentDesign = current ? designOf(current) : null;

    const seen = new Set();
    this.productHandles = handles.filter((handle) => {
      const design = designOf(handle);
      if (currentDesign && design === currentDesign) return false;
      if (seen.has(design)) return false;
      seen.add(design);
      return true;
    });

    this.productList = new MinimogTheme.ProductList(this, this.productHandles);
  }
}
customElements.define("m-recently-viewed", MRecentlyViewed);
