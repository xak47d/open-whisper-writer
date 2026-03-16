# Override the contrib hook for webrtcvad to avoid PackageNotFoundError
# when webrtcvad-wheels is installed instead of webrtcvad.
# The webrtcvad module itself is already collected via hiddenimports.
