# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
# Creative Commons and rights-based license constants.
# These are referenced by User.default_license and MediaPost.license_code.

LICENSE_CC0 = "cc0"
LICENSE_CC_BY = "cc-by"
LICENSE_CC_BY_SA = "cc-by-sa"
LICENSE_CC_BY_ND = "cc-by-nd"
LICENSE_CC_BY_NC = "cc-by-nc"
LICENSE_CC_BY_NC_SA = "cc-by-nc-sa"
LICENSE_CC_BY_NC_ND = "cc-by-nc-nd"
LICENSE_ALL_RIGHTS_RESERVED = "all-rights-reserved"

# Most permissive first
DEFAULT_LICENSE = LICENSE_CC0

LICENSE_CHOICES = [
    (LICENSE_CC0, "CC0 — Public Domain Dedication"),
    (LICENSE_CC_BY, "CC BY — Attribution"),
    (LICENSE_CC_BY_SA, "CC BY-SA — Attribution-ShareAlike"),
    (LICENSE_CC_BY_ND, "CC BY-ND — Attribution-NoDerivatives"),
    (LICENSE_CC_BY_NC, "CC BY-NC — Attribution-NonCommercial"),
    (LICENSE_CC_BY_NC_SA, "CC BY-NC-SA — Attribution-NonCommercial-ShareAlike"),
    (LICENSE_CC_BY_NC_ND, "CC BY-NC-ND — Attribution-NonCommercial-NoDerivatives"),
    (LICENSE_ALL_RIGHTS_RESERVED, "All Rights Reserved"),
]

LICENSE_URLS = {
    LICENSE_CC0: "https://creativecommons.org/publicdomain/zero/1.0/",
    LICENSE_CC_BY: "https://creativecommons.org/licenses/by/4.0/",
    LICENSE_CC_BY_SA: "https://creativecommons.org/licenses/by-sa/4.0/",
    LICENSE_CC_BY_ND: "https://creativecommons.org/licenses/by-nd/4.0/",
    LICENSE_CC_BY_NC: "https://creativecommons.org/licenses/by-nc/4.0/",
    LICENSE_CC_BY_NC_SA: "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    LICENSE_CC_BY_NC_ND: "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    LICENSE_ALL_RIGHTS_RESERVED: "",
}

# Human-readable short names for UI badges
LICENSE_SHORT_LABELS = {
    LICENSE_CC0: "CC0",
    LICENSE_CC_BY: "CC BY",
    LICENSE_CC_BY_SA: "CC BY-SA",
    LICENSE_CC_BY_ND: "CC BY-ND",
    LICENSE_CC_BY_NC: "CC BY-NC",
    LICENSE_CC_BY_NC_SA: "CC BY-NC-SA",
    LICENSE_CC_BY_NC_ND: "CC BY-NC-ND",
    LICENSE_ALL_RIGHTS_RESERVED: "© All Rights Reserved",
}

LICENSE_REQUIRES_ATTRIBUTION = {
    LICENSE_CC0: False,
    LICENSE_CC_BY: True,
    LICENSE_CC_BY_SA: True,
    LICENSE_CC_BY_ND: True,
    LICENSE_CC_BY_NC: True,
    LICENSE_CC_BY_NC_SA: True,
    LICENSE_CC_BY_NC_ND: True,
    LICENSE_ALL_RIGHTS_RESERVED: True,
}
