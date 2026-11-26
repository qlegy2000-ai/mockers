/* Mockers — keeps the garment switcher inside the quick-view modal.
   This must load on EVERY page, not from inside the snippet: the snippet only renders
   on product pages, and <script> tags inside AJAX-parsed HTML never execute — so on a
   collection page nothing was ever bound and the options behaved as plain links. */
(function () {
  if (window.mkStyleSwitcherBound) return;
  window.mkStyleSwitcherBound = true;

  document.addEventListener('click', function (e) {
    var opt = e.target.closest && e.target.closest('.mk-style-opt[data-mk-handle]');
    if (!opt) return;

    /* Only hijack inside the quick-view modal. On a product page a plain link is right. */
    if (!opt.closest('.m-product-quickview')) return;

    var qv = window.MinimogTheme && window.MinimogTheme.ProductQuickView;
    if (!qv || typeof qv.fetchHtml !== 'function') return;   /* let the link work */

    e.preventDefault();
    opt.classList.add('is-loading');

    try {
      /* Swap the modal contents in place.
         Deliberately NOT calling qv.close(): its cleanup runs on a 200ms timer and
         would delete the freshly fetched content. Removing the current panel keeps
         the modal open and avoids that race. */
      var current = document.querySelector('.m-product-quickview');
      if (current) current.remove();
      qv.fetchHtml(opt.getAttribute('data-mk-handle'));
    } catch (err) {
      window.location.href = opt.getAttribute('href');
    }
  });
})();
