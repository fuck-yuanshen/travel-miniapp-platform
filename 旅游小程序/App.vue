<script>
	export default {
		onLaunch: function() {
			console.log('App Launch')
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style>
	/* 每个页面公共样式 */
	page {
		background: #eef3f9;
		color: #1c3656;
		font-family: "PingFang SC", "Helvetica Neue", Arial, sans-serif;
	}

	view, text, input, button {
		box-sizing: border-box;
	}

	.card-shadow {
		box-shadow: 0 14rpx 30rpx rgba(18, 57, 106, 0.08);
	}

	.gradient-primary {
		background: linear-gradient(130deg, #1b75f8 0%, #39a5ff 100%);
	}

	.text-ellipsis {
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
</style>
