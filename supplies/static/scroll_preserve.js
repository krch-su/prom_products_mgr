document.addEventListener('DOMContentLoaded', function () {
      // Get the scroll position from localStorage or set it to 0 if not present
      var scrollPosition = parseInt(localStorage.getItem('adminScrollPosition')) || 0;

      // Set the scroll position on page load
      window.scrollTo(0, scrollPosition);

      // Save the scroll position when the user scrolls
      window.addEventListener('scroll', function () {
        localStorage.setItem('adminScrollPosition', window.scrollY);
      });
    });